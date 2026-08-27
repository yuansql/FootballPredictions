#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日稿 linter：01 单格 Top3 + counter 防格 + HT/FT + TOP2 闸 + 03 RMA（V17.4.20）。"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from receipt_fingerprint import (
    counter_hit_shadow_check,
    fingerprint_from_fields,
    load_ledger,
    shadow_check,
)
from score_geometry import PathLeaf, lint_score_geometry

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
    ("continuation_guest", ("客队刚赢", "同址客胜", "刚赢再战")),
]

RECEIPT_MARKERS = ("【反剧本收据】", "counter_direction=", "counter_one_liner=")
OPENING_MARKERS = ("先破门", "开口", "开场见球", "对方先", "客队先", "主队先")
OVERCONFIDENT_RE = re.compile(r"必胜|铁定|稳了|焊死|闭眼")
CLAUSE_RE = re.compile(r"clause_id\s*[=＝]\s*([^\s｜|\n]+)")
COUNTER_DIR_RE = re.compile(r"counter_direction\s*[=＝]\s*([^\s｜|\n]+)")
# 勿匹配 ht_path_A
PATH_LEAF_RE = re.compile(
    r"(?<![A-Za-z_])path[_＝=]?([A-Za-z0-9]+)\s*[=＝]\s*[^｜|\n]*[｜|]\s*weight\s*[=＝]\s*([0-9]*\.?[0-9]+)\s*[｜|]\s*终场\s*[=＝]\s*(\d+-\d+)",
    re.I,
)
HT_PATH_RE = re.compile(r"ht_path[_＝=]?([A-Za-z0-9]+)\s*[=＝]", re.I)
TOP_BLOCK_RE = re.compile(r"【今晚研究 TOP】(.+?)(?=\n【|\Z)", re.S)
TOP_LINE_RE = re.compile(r"^([123])[\.、]\s*(.+)$", re.M)

RMA_TABLE_RE = re.compile(r"^\|\s*.+\s*\|\s*direction_rework|score_rework|closed", re.M | re.I)


@dataclass
class SectionMeta:
    title: str
    block: str
    direction: str
    tier: str
    weld: str | None
    clause_id: str
    counter_direction: str
    n_paths: int


def _guess_weld_tag(block: str, direction: str) -> str | None:
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
    if tag == "continuation_guest":
        return False  # 降权标签，不强制收据
    if any(m in block for m in RECEIPT_MARKERS):
        return False
    if tag == "revenge_home" and ("防平" in direction or "胶着" in direction):
        return False
    if tag == "weld_draw" and ("客不败" in direction or "并列" in direction):
        return False
    return True


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
    if "结构档=low" in block or "结构档＝low" in block:
        return "low"
    return "high"


def _parse_paths(block: str) -> list[PathLeaf]:
    out: list[PathLeaf] = []
    for m in PATH_LEAF_RE.finditer(block):
        out.append(PathLeaf(m.group(1), float(m.group(2)), m.group(3)))
    return out


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


def lint_ht_ft(block: str, direction: str, weld: str | None) -> list[str]:
    """HT/FT 分轨：德比/焊平/谨慎闷须开口备路径。"""
    issues: list[str] = []
    need = weld in ("derby_caution", "weld_draw") or "谨慎闷" in block
    has_ht = bool(HT_PATH_RE.search(block))
    has_opening = any(w in block for w in OPENING_MARKERS)
    if need and not has_opening:
        issues.append(
            "缺开口/先破门备路径（ht_path 或上半场须写对方先破门；禁只焊谨慎闷半场）"
        )
    elif need and not has_ht and "上半场" not in block:
        issues.append("建议写 ht_path_A/B（半场态与 90′ 终场分轨）")
    if has_ht and "主胜" in direction:
        ht_blob = "\n".join(line for line in block.splitlines() if "ht_path" in line.lower())
        if ht_blob and not any(w in ht_blob for w in ("先破门", "开口", "客队先", "对方先")):
            issues.append("HT 主轴与终场主胜同向时，须有「对方/客队先破门」ht_path 备叶")
    return issues


def _match_top_to_title(desc: str, titles: list[str]) -> str | None:
    for t in titles:
        head = re.split(r"[｜|]", t, maxsplit=1)[0]
        bits = [x for x in re.split(r"\s*vs\s*|\s+", head) if len(x) >= 2]
        if any(b in desc for b in bits):
            return t
    return None


def lint_top2(text: str, metas: list[SectionMeta], ledger: list[dict]) -> list[str]:
    issues: list[str] = []
    m = TOP_BLOCK_RE.search(text)
    if not m:
        return issues
    by_title = {s.title: s for s in metas}
    titles = [s.title for s in metas]
    for lm in TOP_LINE_RE.finditer(m.group(1)):
        slot, desc = lm.group(1), lm.group(2)
        title = _match_top_to_title(desc, titles)
        if not title or title not in by_title:
            continue
        meta = by_title[title]
        if slot == "1" and meta.weld == "continuation_guest":
            issues.append(f"TOP1 {title}: continuation_guest（同址客刚赢）不得进 TOP1")
        if slot != "2":
            continue
        if meta.tier == "low":
            issues.append(f"TOP2 {title}: 低结构/胶着不得进 TOP2（V17.4.20）")
        if OVERCONFIDENT_RE.search(meta.block) and meta.tier == "low":
            issues.append(f"TOP2 {title}: 01 嘴硬（必/铁定）但结构档低，踢出 TOP2")
        if meta.weld and meta.weld != "continuation_guest":
            if not meta.clause_id:
                issues.append(f"TOP2 {title}: 焊标签须 clause_id 绑 path 叶")
            if meta.n_paths < 1:
                issues.append(f"TOP2 {title}: 提名须有情景路径叶（weight｜终场）")
        if meta.weld and meta.clause_id and meta.counter_direction:
            fp = fingerprint_from_fields(
                meta.weld, meta.clause_id, meta.counter_direction, 4
            )
            sv = counter_hit_shadow_check(fp, ledger, threshold=1)
            if sv.would_demote:
                issues.append(f"TOP2 {title}: {sv.reason}")
    return issues


def _lint_section(block: str, title: str) -> tuple[list[str], SectionMeta | None]:
    issues: list[str] = []
    m = DIR_SCORE_RE.search(block)
    if not m:
        issues.append(f"{title}: 缺 **方向｜比分** 行")
        return issues, None
    direction, tail = m.group(1).strip(), m.group(2).strip()
    main, sub, defense, pang = _split_scores(tail)
    if not main:
        issues.append(f"{title}: 未解析到主推比分")
        return issues, None
    abstain = "弃权" in tail or "防：弃权" in tail or "防:**弃权" in block
    tier = _guess_structure(direction, block)
    weld = _guess_weld_tag(block, direction)
    tags = [weld] if weld else []
    band = _parse_goals_band(block)
    paths = _parse_paths(block)
    cm = COUNTER_DIR_RE.search(block)
    counter_direction = cm.group(1).strip() if cm else ""
    cl = CLAUSE_RE.search(block)
    clause_id = cl.group(1).strip() if cl else ""
    geo = lint_score_geometry(
        tier,
        main,
        sub or main,
        "弃权" if abstain else (defense or sub or main),
        旁=pang,
        direction_tags=tags,
        defense_abstain=abstain,
        goals_band=band,
        direction_text=direction,
        paths=paths or None,
        require_paths=False,
        counter_direction=counter_direction,
    )
    for g in geo:
        issues.append(f"{title}: [{g.code}] {g.message}")
    if tier == "high" and not paths:
        issues.append(
            f"{title}: [missing_scenario_paths] 高结构建议写【情景路径】"
            "（weight｜终场）供单格权重排序（V17.4.20 warn）"
        )
    if _needs_receipt(block, direction, weld):
        issues.append(f"{title}: 疑似 {weld} 焊叙事但未写【反剧本收据】（V17.4.15）")
    if OVERCONFIDENT_RE.search(block) and tier == "low":
        issues.append(f"{title}: [overconfident_low_structure] 低结构禁必/铁定口吻")
    for ht in lint_ht_ft(block, direction, weld):
        issues.append(f"{title}: [ht_ft] {ht}")
    if weld == "continuation_guest" and "主胜" in direction:
        issues.append(
            f"{title}: [continuation_guest] 同址客刚赢：研究星封顶★★★、默认不进 TOP2"
            "（除非客上轮净胜≤1 且主核心缺阵≥2）"
        )
    meta = SectionMeta(
        title=title,
        block=block,
        direction=direction,
        tier=tier,
        weld=weld,
        clause_id=clause_id,
        counter_direction=counter_direction,
        n_paths=len(paths),
    )
    return issues, meta


def lint_01(path: Path, ledger: list[dict] | None = None) -> list[str]:
    text = path.read_text(encoding="utf-8")
    issues: list[str] = []
    sections = list(SECTION_RE.finditer(text))
    if not sections:
        issues.append(f"{path.name}: 无 ## 场次 段")
        return issues

    metas: list[SectionMeta] = []
    for i, sec in enumerate(sections):
        start = sec.start()
        end = sections[i + 1].start() if i + 1 < len(sections) else len(text)
        block = text[start:end]
        title = sec.group(1).strip()
        extra, meta = _lint_section(block, title)
        issues.extend(extra)
        if meta:
            metas.append(meta)

    if ledger is None:
        ledger = load_ledger(ROOT / "data/miss_fingerprint_ledger.jsonl")
    issues.extend(lint_top2(text, metas, ledger))
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
    ledger = load_ledger(ROOT / "data/miss_fingerprint_ledger.jsonl")
    if f01.is_file():
        issues.extend(lint_01(f01, ledger))
    if f03.is_file():
        issues.extend(lint_03(f03))
    return issues


def main() -> int:
    ap = argparse.ArgumentParser(description="Lint toutiao drafts for V17.4.20 hooks")
    ap.add_argument("path", nargs="?", help="01.md / 03.md / YYYY-MM-DD 日夹")
    ap.add_argument("--warn-only", action="store_true", help="只打印，exit 0")
    args = ap.parse_args()

    if not args.path:
        ap.print_help()
        return 0

    p = Path(args.path).expanduser().resolve()
    issues: list[str] = []
    ledger = load_ledger(ROOT / "data/miss_fingerprint_ledger.jsonl")
    if p.is_dir():
        issues = lint_day_dir(p)
    elif p.name.startswith("01"):
        issues = lint_01(p, ledger)
    elif p.name.startswith("03"):
        issues = lint_03(p)
    else:
        print(f"unknown path: {p}", file=sys.stderr)
        return 2

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
