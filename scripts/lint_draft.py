#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日稿 linter：01 单格 Top3 + counter 防格 + HT/FT + TOP2 闸 + 03 RMA（V17.4.22.3）。"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from receipt_fingerprint import (
    counter_hit_shadow_check,
    fingerprint_from_fields,
    load_ledger,
    shadow_check,
)
from rma_route import atoms_from_scores
from rule_tools import ReceiptRuleTool, REGISTRY
from score_geometry import PathLeaf, lint_score_geometry

ROOT = Path(__file__).resolve().parents[1]

DAY_RE = re.compile(r"(20\d{2}-\d{2}-\d{2})")
# 命中率 1/3、7/9；不吃 2-1/1-1 比分篮
HITRATE_RE = re.compile(r"(?<![\d.\-])(\d{1,2})/(\d{1,2})(?![\d.\-])")
NAIL_RE = re.compile(r"今晚我钉[一二三四五六七八九1-9]场")
EMPTY_TOP2_RE = re.compile(r"无高结构\s*TOP2|今晚不设\s*TOP2|宁缺：无高结构")
ANALOGY_RE = re.compile(r"里昂课|结构同类")
SIGN_TRIPLE_RE = re.compile(
    r"符号三元组|(追分|领先).{0,32}(主|客)|(主|客).{0,32}(追分|领先)"
)
BOOK_LABELS = ("对外三场", "01篮", "全表")
SLOT_RULE_DAY = date(2026, 8, 28)
BOOK_RULE_DAY = date(2026, 8, 27)
ATOM_RULE_DAY = date(2026, 8, 31)
DIR_MUST_DAY = date(2026, 9, 2)

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

RMA_TABLE_RE = re.compile(
    r"^\|\s*.+\s*\|\s*direction_rework|score_rework|closed|skip", re.M | re.I
)
BUDING_RE = re.compile(r"不钉方向")
LOCK_RE = re.compile(r"锁平|锁主|锁客")
DIR_ATOM_RE = re.compile(r"主不败|客不败|锁主|锁客|锁平")
VACANT_02_RE = re.compile(r"空槽|方向空着|不锁\s*1X2")
SCORE_ABSTAIN_RE = re.compile(r"比分弃权|不写比分|比分\s*[：:]\s*[—\-]")
BESIDE_RE = re.compile(r"放旁边")
SCORE_TOKEN_RE = re.compile(r"(\d+-\d+)")
TRUE00_RE = re.compile(r"闷平|TRUE_00|死盒|焊平")
STEAL_SCORES = frozenset({"0-1", "1-2"})
WHY_REJECT_RE = re.compile(r"why_reject\s*[=＝]", re.I)


def parse_draft_day(path: Path) -> date | None:
    m = DAY_RE.search(str(path))
    if not m:
        return None
    y, mo, d = (int(x) for x in m.group(1).split("-"))
    return date(y, mo, d)


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
    rule_verdicts: list[dict] = None

    def __post_init__(self):
        if self.rule_verdicts is None:
            self.rule_verdicts = []


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


def _has_direction_atom(direction: str) -> bool:
    if "胶着" in direction:
        return False
    if DIR_ATOM_RE.search(direction):
        return True
    return bool(re.search(r"主胜|客胜|平局", direction))


def _lint_dir_must(direction: str, title: str, day: date | None) -> list[str]:
    if day is None or day < DIR_MUST_DAY:
        return []
    if "胶着" in direction:
        return [f"{title}: 禁用胶着，改主不败/客不败或锁主/锁客/锁平"]
    if not _has_direction_atom(direction):
        return [f"{title}: 方向必须给（锁* 或 主不败/客不败）"]
    return []


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


def _lint_section(
    block: str, title: str, *, day: date | None = None
) -> tuple[list[str], SectionMeta | None]:
    issues: list[str] = []
    m = DIR_SCORE_RE.search(block)
    if not m:
        issues.append(f"{title}: 缺 **方向｜比分** 行")
        return issues, None
    direction, tail = m.group(1).strip(), m.group(2).strip()
    issues.extend(_lint_dir_must(direction, title, day))
    main, sub, defense, pang = _split_scores(tail)
    score_abstain = bool(SCORE_ABSTAIN_RE.search(tail) or SCORE_ABSTAIN_RE.search(block))
    if not main:
        if day is not None and day >= DIR_MUST_DAY and score_abstain:
            if not _parse_goals_band(block) and "进球数" not in block:
                issues.append(f"{title}: 比分弃权须写进球数")
        else:
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
    if main:
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
    if day is not None and day >= ATOM_RULE_DAY:
        issues.extend(lint_unpinned_home_weld(block, direction, title, pang, paths))
    if OVERCONFIDENT_RE.search(block) and tier == "low":
        issues.append(f"{title}: [overconfident_low_structure] 低结构禁必/铁定口吻")
    if (
        day is not None
        and day >= SLOT_RULE_DAY
        and day < DIR_MUST_DAY
        and "胶着" in direction
    ):
        rm = re.search(r"胜平负[：:]\s*([^\n｜]+)", block)
        if rm:
            pub = rm.group(1)
            if "胶着" not in pub and "并列" not in pub:
                issues.append(
                    f"{title}: 01 方向胶着，研究行胜平负不得收成更窄（{pub.strip()}）"
                )
    for ht in lint_ht_ft(block, direction, weld):
        issues.append(f"{title}: [ht_ft] {ht}")
    if weld == "continuation_guest" and "主胜" in direction:
        issues.append(
            f"{title}: [continuation_guest] 同址客刚赢：研究星封顶★★★、默认不进 TOP2"
            "（除非客上轮净胜≤1 且主核心缺阵≥2）"
        )
    # Phase A: instrument with RuleTool PoC (receipt rule)
    rule_tool = ReceiptRuleTool()
    rv = rule_tool.run(
        {"block": block, "direction": direction, "weld_tag": weld}
    )
    rule_verdicts = [rv.__dict__]
    if rv.verdict in ("FORBID", "FLAG") and rv.message:
        issues.append(f"{title}: [RuleTool:{rv.rule_id}] {rv.message}")

    meta = SectionMeta(
        title=title,
        block=block,
        direction=direction,
        tier=tier,
        weld=weld,
        clause_id=clause_id,
        counter_direction=counter_direction,
        n_paths=len(paths),
        rule_verdicts=rule_verdicts,
    )
    return issues, meta


def lint_01(path: Path, ledger: list[dict] | None = None) -> list[str]:
    text = path.read_text(encoding="utf-8")
    issues: list[str] = []
    day = parse_draft_day(path)
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
        extra, meta = _lint_section(block, title, day=day)
        issues.extend(extra)
        if meta:
            metas.append(meta)

    if ledger is None:
        ledger = load_ledger(ROOT / "data/miss_fingerprint_ledger.jsonl")
    issues.extend(lint_top2(text, metas, ledger))
    if day is not None and day >= SLOT_RULE_DAY:
        if ANALOGY_RE.search(text) and not SIGN_TRIPLE_RE.search(text):
            issues.append(
                f"{path.name}: 写了里昂课/结构同类但缺符号三元组（追分|领先 × 主|客）"
            )
    return issues


def lint_03_books(text: str, day: date | None, name: str) -> list[str]:
    if day is not None and day < BOOK_RULE_DAY:
        return []
    if not HITRATE_RE.search(text):
        return []
    missing = [lab for lab in BOOK_LABELS if lab not in text]
    if missing:
        return [
            f"{name}: 出现命中率分数但缺三本账标签 {','.join(missing)}（对外三场/01篮/全表）"
        ]
    return []


def lint_02_nail(day_dir: Path) -> list[str]:
    day = parse_draft_day(day_dir)
    if day is None or day < SLOT_RULE_DAY:
        return []
    f01 = day_dir / "01-竞彩分析.md"
    f02 = day_dir / "02-头条正文.txt"
    if not f02.is_file():
        html = day_dir / "02-头条正文.html"
        if html.is_file():
            f02 = html
        else:
            return []
    t02 = f02.read_text(encoding="utf-8")
    issues: list[str] = []
    if NAIL_RE.search(t02) and "别拿主胜凑席" in t02:
        issues.append(f"{f02.name}: 「钉K场」与「别拿主胜凑席」不得同文（看槽≠钉槽）")
    if f01.is_file() and EMPTY_TOP2_RE.search(f01.read_text(encoding="utf-8")) and NAIL_RE.search(t02):
        issues.append(f"{f02.name}: 01 已宁缺 TOP2，禁止「今晚我钉三场」枚举方向")
    issues.extend(lint_02_atom_text(t02) if day >= ATOM_RULE_DAY else [])
    issues.extend(lint_02_must_direction(t02, day))
    return issues


def _plain_02(text: str) -> str:
    t = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return t.replace("**", " ")


def surface_1x2_tokens(window: str) -> set[str]:
    """句面 1X2。排除主队/客队；放旁边只认紧贴的主/客。"""
    t = window.replace("主队", "\u0000").replace("客队", "\u0000")
    out: set[str] = set()
    if "主不败" in t:
        return {"主胜", "平"}
    if "客不败" in t:
        return {"客胜", "平"}
    if "锁平" in t:
        out.add("平")
    if "锁主" in t or "主胜" in t:
        out.add("主胜")
    if "锁客" in t or "客胜" in t:
        out.add("客胜")
    for m in BESIDE_RE.finditer(t):
        prefix = t[max(0, m.start() - 8) : m.start()]
        if "客" in prefix:
            out.add("客胜")
        if "主" in prefix:
            out.add("主胜")
    return out


def _lock_draw_ok(window: str, scores: list[str]) -> bool:
    if "0-0" in scores:
        return True
    return bool(TRUE00_RE.search(window))


def lint_unpinned_home_weld(
    block: str,
    direction: str,
    title: str,
    pang: str | None,
    paths: list[PathLeaf],
) -> list[str]:
    """V17.4.22.1：主胜防平 + 页上客胜偷球格 ⇒ 须活收据。胶着 scout 不触发。"""
    if "胶着" in direction:
        return []
    pub = ""
    rm = re.search(r"胜平负[：:]\s*([^\n｜]+)", block)
    if rm:
        pub = rm.group(1)
    blob = f"{direction} {pub}"
    if "主胜" not in blob or "防平" not in blob:
        return []
    steal: set[str] = set()
    if pang in STEAL_SCORES:
        steal.add(pang)
    steal.update(p.score for p in paths if p.score in STEAL_SCORES)
    for m in re.finditer(r"旁挂[^\n]{0,40}", block):
        steal.update(s for s in SCORE_TOKEN_RE.findall(m.group(0)) if s in STEAL_SCORES)
    if not steal:
        return []
    cm = COUNTER_DIR_RE.search(block)
    counter = cm.group(1).strip() if cm else ""
    live = any(m in block for m in RECEIPT_MARKERS) and (
        "客胜" in counter or bool(WHY_REJECT_RE.search(block))
    )
    if live:
        return []
    return [
        f"{title}: 主胜防平且页上有客胜偷球 {sorted(steal)}，"
        "须活【反剧本收据】（counter_direction=客胜 / why_reject 点名该偷）"
    ]


def lint_02_atom_text(text: str) -> list[str]:
    """V17.4.22.1：空槽合法（旧稿）；有锁则一原子；4.22.3 主不败/客不败可两向。"""
    plain = _plain_02(text)
    issues: list[str] = []
    for i, m in enumerate(BUDING_RE.finditer(plain), start=1):
        window = plain[m.start() : m.start() + 320]
        if BESIDE_RE.search(window):
            issues.append(f"02 不钉#{i}: 禁止「放旁边」当第三向")
        scores = SCORE_TOKEN_RE.findall(window)[:2]
        atoms = atoms_from_scores(scores)
        claimed = surface_1x2_tokens(window) | atoms
        dc_home = "主不败" in window
        dc_away = "客不败" in window
        if dc_home:
            extra = atoms - {"主胜", "平"}
            if extra:
                issues.append(f"02 不钉#{i}: 主不败篮不得含 {extra}")
        elif dc_away:
            extra = atoms - {"客胜", "平"}
            if extra:
                issues.append(f"02 不钉#{i}: 客不败篮不得含 {extra}")
        elif len(scores) >= 2 and len(atoms) != 1:
            issues.append(
                f"02 不钉#{i}: 两格 {scores[0]}/{scores[1]} 并集={atoms}，禁止刷两个 1X2"
            )
        elif len(claimed) > 1:
            issues.append(
                f"02 不钉#{i}: 句面+格子 1X2={claimed}，须单例（升锁或划场）"
            )
        if "锁平" in window and not _lock_draw_ok(window, scores):
            issues.append(
                f"02 不钉#{i}: 锁平须含 0-0 或闷平/TRUE_00/死盒/焊平，犹豫不是平"
            )
    return issues


def lint_02_must_direction(text: str, day: date | None) -> list[str]:
    """V17.4.22.3：认真拆的场必须给方向原子；禁胶着、禁空槽。"""
    if day is None or day < DIR_MUST_DAY:
        return []
    plain = _plain_02(text)
    issues: list[str] = []
    if "胶着" in plain:
        issues.append("02: 禁用胶着")
    if VACANT_02_RE.search(plain):
        issues.append("02: 方向必须给，禁止空槽/方向空着")
    n_fields = len(re.findall(r"上半场剧本", plain))
    n_dir = len(DIR_ATOM_RE.findall(plain))
    if n_fields and n_dir < n_fields:
        issues.append(
            f"02: 认真拆 {n_fields} 场，方向原子 {n_dir}（须主不败/客不败/锁*）"
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
    issues.extend(lint_03_books(text, parse_draft_day(path), path.name))
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
    issues.extend(lint_02_nail(day_dir))
    return issues


def _self_check() -> None:
    assert parse_draft_day(Path("drafts/2026-08-27/03-复盘.md")) == date(2026, 8, 27)
    assert HITRATE_RE.search("方向 1/3")
    assert HITRATE_RE.search("| **对外三场** | 1/3 | 0/3 |")
    assert not HITRATE_RE.search("2-1/1-1")
    miss = lint_03_books("方向 1/3", date(2026, 8, 27), "x.md")
    assert miss and "三本账" in miss[0]
    assert not lint_03_books(
        "方向 1/3\n对外三场\n01篮\n全表9场", date(2026, 8, 27), "x.md"
    )
    if not lint_03_books("方向 1/3", date(2026, 8, 15), "x.md"):
        pass
    else:
        raise AssertionError("pre-book-day should skip")
    vacant = lint_02_atom_text("这场我不钉方向。上下半场另说，今晚不锁 1X2。")
    assert vacant == [], vacant
    mixed = lint_02_atom_text(
        "这场我不钉方向。比分心里更近**1-1** 和 **2-1**，客胜放旁边。"
    )
    assert any("放旁边" in x for x in mixed), mixed
    assert any("并集" in x or "1X2" in x for x in mixed), mixed
    assert not any("须写锁" in x for x in mixed), mixed
    napoli = lint_02_atom_text(
        "这场我不钉方向。锁平。比分心里更近**1-1** 和 **0-0**，客胜放旁边。"
    )
    assert any("放旁边" in x or "句面" in x or "单例" in x for x in napoli), napoli
    lock_no_true00 = lint_02_atom_text(
        "这场我不钉方向。锁平。比分心里更近**1-1** 和 **2-2**。"
    )
    assert any("闷平" in x or "TRUE_00" in x or "0-0" in x for x in lock_no_true00), (
        lock_no_true00
    )
    good = lint_02_atom_text(
        "这场我不钉方向。锁平。比分心里更近**1-1** 和 **0-0**。"
    )
    assert good == [], good
    good_away = lint_02_atom_text(
        "这场我不钉方向。锁客。比分心里更近**1-2** 和 **0-1**。"
    )
    assert good_away == [], good_away
    good_shutout = lint_02_atom_text(
        "这场我不钉方向。锁客。比分心里更近**0-2** 和 **0-1**。"
    )
    assert good_shutout == [], good_shutout
    good_home = lint_02_atom_text(
        "这场我不钉方向。锁主。比分心里更近**2-1** 和 **1-0**。"
    )
    assert good_home == [], good_home
    steal_home = """**方向｜比分**：主胜（防平）｜**2-1** 主推 / **1-1** 次 / 防：**弃权**（旁挂 **0-1**）
path_D = 偷 ｜ weight = 0.15 ｜ 终场 = 0-1
"""
    steal_iss, _ = _lint_section(steal_home, "塞尔塔", day=ATOM_RULE_DAY)
    assert any("收据" in x or "不钉锁主" in x or "偷球" in x for x in steal_iss), steal_iss
    scout = """**方向｜比分**：胶着偏主｜**2-1** 主推 / **1-1** 次 / 防：**弃权**（旁挂 **0-1**）
"""
    scout_iss, _ = _lint_section(scout, "胶着scout", day=ATOM_RULE_DAY)
    assert not any("偷球" in x or "不钉锁主" in x for x in scout_iss), scout_iss
    dc_ok = lint_02_atom_text(
        "这场我不钉方向。主不败。比分心里更近**1-0** 和 **1-1**。"
    )
    assert dc_ok == [], dc_ok
    dc_bad = lint_02_atom_text(
        "这场我不钉方向。主不败。比分心里更近**1-0** 和 **0-1**。"
    )
    assert any("主不败" in x for x in dc_bad), dc_bad
    vacant_new = lint_02_must_direction(
        "上半场剧本：客队先压。这场方向空着，不锁 1X2。", DIR_MUST_DAY
    )
    assert any("方向必须给" in x or "空槽" in x or "空着" in x for x in vacant_new), (
        vacant_new
    )
    ok_dir = lint_02_must_direction(
        "上半场剧本：主队先顶。这场主不败。", DIR_MUST_DAY
    )
    assert ok_dir == [], ok_dir
    jiao_new, _ = _lint_section(scout, "胶着scout", day=DIR_MUST_DAY)
    assert any("胶着" in x for x in jiao_new), jiao_new
    abstain = """**方向｜比分**：客不败｜比分弃权
研究 ★★★☆☆｜胜平负：客不败｜进球数：一至三球
"""
    ab_iss, ab_meta = _lint_section(abstain, "弃权场", day=DIR_MUST_DAY)
    assert ab_meta is not None
    assert not any("未解析到主推比分" in x for x in ab_iss), ab_iss
    print("OK lint_draft self-check")


def main() -> int:
    ap = argparse.ArgumentParser(description="Lint toutiao drafts for V17.4.22.3 hooks")
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
