#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日稿 linter：01 邻格簇几何 + 进球档 + 03 RMA（V17.4.17）。"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from receipt_fingerprint import fingerprint_from_fields, load_ledger, shadow_check
from score_geometry import lint_score_geometry

ROOT = Path(__file__).resolve().parents[1]

SECTION_RE = re.compile(r"^##\s+场次[｜|](.+)$", re.M)
DIR_SCORE_RE = re.compile(
    r"\*\*方向｜比分(?:（[^）]+）)?\*\*[：:]\s*(.+?)｜\s*(.+)$",
    re.M,
)
SCORE_PART_RE = re.compile(
    r"\*\*(\d+-\d+)\*\*\s*(主推|次|防)|旁挂[^\*]*\*\*(\d+-\d+)\*\*|旁\s*(\d+-\d+)",
    re.I,
)
# 进球数：2–3 / 2或者3球 / 进球 2-3
GOALS_BAND_RE = re.compile(
    r"进球数[：:]\s*([^\n｜|]{1,24})|进球[数区间]*[：:\s]*(\d)\s*[–\-~/到至或]+\s*(\d)",
    re.I,
)
GOALS_RANGE_RE = re.compile(r"(\d)\s*[–\-~/到至或]+\s*(\d)")
WELD_HINTS: list[tuple[str, tuple[str, ...]]] = [
    ("revenge_home", ("讨债", "同址刚", "三日再战")),
    ("weld_draw", ("焊平", "平局味最浓")),
    ("manage_tie", ("管理比赛", "输一场仍晋级", "晋级≠90")),
    ("derby_caution", ("德比", "同城德比")),
]

RECEIPT_MARKERS = ("【反剧本收据】", "counter_direction=", "counter_one_liner=")


def _guess_weld_tag(block: str, direction: str) -> str | None:
    """按命中词数取最强标签；弱匹配不触发。"""
    best: tuple[int, str] | None = None
    for tag, words in WELD_HINTS:
        hits = sum(1 for w in words if w in block)
        if tag == "weld_draw" and direction.strip() in ("平", "平局"):
            hits += 2
        if tag == "revenge_home" and "主胜" in direction and ("讨债" in block or "同址" in block):
            hits += 1
        if hits and (best is None or hits > best[0]):
            best = (hits, tag)
    if best and best[0] >= 2:
        return best[1]
    return None


def _needs_receipt(block: str, direction: str, tag: str | None) -> bool:
    if not tag:
        return False
    if any(m in block for m in RECEIPT_MARKERS):
        return False
    # 有防平/客不败/并列 → 未焊死，不强制收据
    if tag == "revenge_home" and ("防平" in direction or "胶着" in direction):
        return False
    if tag == "weld_draw" and ("客不败" in direction or "并列" in direction):
        return False
    return True

RMA_TABLE_RE = re.compile(r"^\|\s*.+\s*\|\s*direction_rework|score_rework|closed", re.M | re.I)


def _split_scores(tail: str) -> tuple[str, str, str, str | None]:
    main = sub = defense = ""
    pang: str | None = None
    for m in SCORE_PART_RE.finditer(tail):
        if m.group(1) and m.group(2):
            label = m.group(2)
            score = m.group(1)
            if label == "主推":
                main = score
            elif label == "次":
                sub = score
            elif label == "防":
                defense = score
        elif m.group(3):
            pang = m.group(3)
        elif m.group(4):
            pang = m.group(4)
    return main, sub, defense, pang


def _guess_structure(direction: str, block: str) -> str:
    if any(x in direction for x in ("胶着", "并列", "客不败", "主不败")):
        return "low"
    if "平" in direction and "防" in direction:
        return "low"
    tag = _guess_weld_tag(block, direction)
    if tag in ("weld_draw", "manage_tie") and "焊" in block:
        return "low"
    return "high"


def _parse_goals_band(block: str) -> set[int] | None:
    m = GOALS_BAND_RE.search(block)
    if not m:
        return None
    chunk = (m.group(1) or "").strip()
    if m.group(2) and m.group(3):
        return {int(m.group(2)), int(m.group(3))}
    if chunk:
        rm = GOALS_RANGE_RE.search(chunk)
        if rm:
            return {int(rm.group(1)), int(rm.group(2))}
        digits = re.findall(r"\d", chunk)
        if len(digits) >= 2:
            return {int(digits[0]), int(digits[1])}
        if len(digits) == 1:
            return {int(digits[0])}
    return None


def lint_01(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    issues: list[str] = []
    sections = list(SECTION_RE.finditer(text))
    if not sections:
        issues.append(f"{path.name}: 无 ## 场次 段")
        return issues

    for i, sec in enumerate(sections):
        start = sec.start()
        end = sections[i + 1].start() if i + 1 < len(sections) else len(text)
        block = text[start:end]
        title = sec.group(1).strip()
        m = DIR_SCORE_RE.search(block)
        if not m:
            issues.append(f"{title}: 缺 **方向｜比分** 行")
            continue
        direction, tail = m.group(1).strip(), m.group(2).strip()
        main, sub, defense, pang = _split_scores(tail)
        if not main:
            issues.append(f"{title}: 未解析到主推比分")
            continue
        abstain = "弃权" in tail or "防：弃权" in tail or "防:**弃权" in block
        tier = _guess_structure(direction, block)
        weld = _guess_weld_tag(block, direction)
        tags = [weld] if weld else []
        band = _parse_goals_band(block)
        geo = lint_score_geometry(
            tier,
            main,
            sub or main,
            "弃权" if abstain else (defense or sub or main),
            旁=pang,
            direction_tags=tags,
            defense_abstain=abstain,
            goals_band=band,
        )
        for g in geo:
            issues.append(f"{title}: [{g.code}] {g.message}")
        if _needs_receipt(block, direction, weld):
            issues.append(
                f"{title}: 疑似 {weld} 焊叙事但未写【反剧本收据】（V17.4.15）"
            )
    return issues


def lint_03(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    issues: list[str] = []
    if "RMA" not in text and "direction_rework" not in text:
        issues.append(f"{path.name}: 缺 RMA 路由表（V17.4.16）")
    elif not RMA_TABLE_RE.search(text):
        issues.append(f"{path.name}: RMA 表无 direction_rework/score_rework/closed 行")
    if "三问" not in text:
        issues.append(f"{path.name}: 缺三问声明")
    return issues


def lint_day_dir(day_dir: Path) -> list[str]:
    issues: list[str] = []
    f01 = day_dir / "01-竞彩分析.md"
    f03 = day_dir / "03-复盘.md"
    if f01.is_file():
        issues.extend(lint_01(f01))
    if f03.is_file():
        issues.extend(lint_03(f03))
    return issues


def main() -> int:
    ap = argparse.ArgumentParser(description="Lint toutiao drafts for V17.4.17 hooks")
    ap.add_argument("path", nargs="?", help="01.md / 03.md / YYYY-MM-DD 日夹")
    ap.add_argument("--warn-only", action="store_true", help="只打印，exit 0")
    args = ap.parse_args()

    if not args.path:
        ap.print_help()
        return 0

    p = Path(args.path).expanduser().resolve()
    issues: list[str] = []
    if p.is_dir():
        issues = lint_day_dir(p)
    elif p.name.startswith("01"):
        issues = lint_01(p)
    elif p.name.startswith("03"):
        issues = lint_03(p)
    else:
        print(f"unknown path: {p}", file=sys.stderr)
        return 2

    ledger = load_ledger(ROOT / "data/miss_fingerprint_ledger.jsonl")
    fp = fingerprint_from_fields("revenge_home", "script#1", "客胜", 4)
    sv = shadow_check(fp, ledger, threshold=2)
    if sv.would_demote:
        issues.append(f"SHADOW fingerprint: {sv.reason}")

    if issues:
        print(f"LINT {p.name} ({len(issues)} issue(s))")
        for i in issues:
            print(f"  - {i}")
        return 0 if args.warn_only else 1
    print(f"PASS lint {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
