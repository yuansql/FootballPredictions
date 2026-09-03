#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RMA 双仓路由：方向返修 vs 比分返修（V17.4.16 · 对外 4.22.3 方向必给）。"""
from __future__ import annotations

import re
from enum import Enum
from typing import Iterable, Sequence


class RmaRoute(str, Enum):
    DIRECTION_REWORK = "direction_rework"
    SCORE_REWORK = "score_rework"
    CLOSED = "closed"
    SKIP = "skip"  # 仅遗留空槽：不进分母。4.22.3 起新稿禁止空槽


_SCORE_RE = re.compile(r"^\s*(\d+)\s*[-:：]\s*(\d+)\s*$")


def parse_score(score: str) -> tuple[int, int] | None:
    m = _SCORE_RE.match(score.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def outcome_1x2(home: int, away: int) -> str:
    if home > away:
        return "主胜"
    if home < away:
        return "客胜"
    return "平"


def normalize_direction(text: str) -> set[str]:
    """解析研究/对外方向允许集。

    4.22.3：主不败={主,平}，客不败={客,平}。禁止用裸「不败」两边都加。
    「胶着」仍三向——只为读旧 01；新稿 lint 禁写。
    「并列」只并所写的边。
    """
    t = text.strip()
    if "主不败" in t:
        return {"主胜", "平"}
    if "客不败" in t:
        return {"客胜", "平"}
    out: set[str] = set()
    if "胶着" in t:
        out.update({"主胜", "平", "客胜"})
        return out
    if "主胜" in t or "锁主" in t:
        out.add("主胜")
    if "客胜" in t or "锁客" in t:
        out.add("客胜")
    if "锁平" in t or ( "平" in t and "防平" not in t):
        out.add("平")
    if not out and t:
        out.add(t)
    return out


def direction_hit(research_direction: str, actual: str) -> bool:
    allowed = normalize_direction(research_direction)
    return actual in allowed


def score_in_basket(actual: str, basket: Sequence[str]) -> bool:
    act = parse_score(actual)
    if act is None:
        return False
    for item in basket:
        s = parse_score(item)
        if s == act:
            return True
    return False


def atoms_from_scores(scores: Iterable[str]) -> set[str]:
    """比分格推出的 1X2 集合（并集）。"""
    out: set[str] = set()
    for item in scores:
        parsed = parse_score(str(item))
        if parsed:
            out.add(outcome_1x2(*parsed))
    return out


def public_allowed_set(surface: str, grid: Sequence[str] | None = None) -> set[str]:
    """对外方向允许集。4.22.3：主不败/客不败/锁* 先于格子；空槽仍 ∅（旧稿）。"""
    t = (surface or "").strip()
    if "锁平" in t:
        return {"平"}
    if "锁主" in t:
        return {"主胜"}
    if "锁客" in t:
        return {"客胜"}
    if "主不败" in t:
        return {"主胜", "平"}
    if "客不败" in t:
        return {"客胜", "平"}
    if "空槽" in t:
        return set()
    atoms = atoms_from_scores(grid or [])
    if atoms:
        return atoms
    if "胶着" in t:
        if "偏主" in t:
            return {"主胜", "平"}
        if "偏客" in t:
            return {"客胜", "平"}
        return set()
    return normalize_direction(t)


def classify_miss(label: str, claim: set[str], actual_1x2: str) -> str | None:
    """A=允许集没有实战 1X2；lean_flip=偏X 反号；None=方向命中。"""
    if actual_1x2 in claim:
        return None
    if "偏客" in label and actual_1x2 == "主胜":
        return "lean_flip"
    if "偏主" in label and actual_1x2 == "客胜":
        return "lean_flip"
    return "A"


def score_miss_class(actual_score: str, basket: Sequence[str]) -> str | None:
    """比分仓分类。None=篮内命中；屠杀净≥4 且篮无净≥3 → 合同外（不提案改 skill）。"""
    if score_in_basket(actual_score, basket):
        return None
    parsed = parse_score(actual_score)
    if parsed is None:
        return "in_contract_pack"
    gd = abs(parsed[0] - parsed[1])
    has_blow = any(
        (p := parse_score(item)) is not None and abs(p[0] - p[1]) >= 3
        for item in basket
    )
    if gd >= 4 and not has_blow:
        return "contract_out_blowout"
    return "in_contract_pack"


def route_rma_public(
    surface: str,
    actual_1x2: str,
    scores_basket: Iterable[str],
    actual_score: str,
) -> RmaRoute:
    """对外复盘路由。无比分篮且方向命中 → closed（比分弃权不计比分仓）。"""
    grid = list(scores_basket)
    claim = public_allowed_set(surface, grid)
    if not claim:
        return RmaRoute.SKIP
    if actual_1x2 not in claim:
        return RmaRoute.DIRECTION_REWORK
    if not grid:
        return RmaRoute.CLOSED
    if score_in_basket(actual_score, grid):
        return RmaRoute.CLOSED
    return RmaRoute.SCORE_REWORK



def route_rma(
    research_direction: str,
    actual_1x2: str,
    scores_basket: Iterable[str],
    actual_score: str,
) -> RmaRoute:
    """方向 miss → direction_rework；方向对但比分未挂 → score_rework；否则 closed。"""
    if not direction_hit(research_direction, actual_1x2):
        return RmaRoute.DIRECTION_REWORK
    if score_in_basket(actual_score, list(scores_basket)):
        return RmaRoute.CLOSED
    return RmaRoute.SCORE_REWORK


def _self_check() -> None:
    # 08-25 森林：主推主胜，实际客胜 0-2
    assert route_rma("主胜（防平）", "客胜", ["2-1", "1-0", "1-1", "0-1"], "0-2") == RmaRoute.DIRECTION_REWORK
    # 08-25 林茨：主胜对，4-1 未进篮
    assert route_rma("主胜（90′）", "主胜", ["2-1", "1-0", "1-1", "0-1"], "4-1") == RmaRoute.SCORE_REWORK
    # 博德：主胜对，2-0 在篮内 → closed
    assert route_rma("主胜", "主胜", ["2-1", "2-0", "1-1", "3-1"], "2-0") == RmaRoute.CLOSED
    # 3-0 同族但未进精确分 → score_rework
    assert route_rma("主胜", "主胜", ["2-1", "2-0", "1-1", "3-1"], "3-0") == RmaRoute.SCORE_REWORK
    # 08-27 费伦茨：并列 ≠ 三向；4-0 主胜是方向穿
    assert normalize_direction("平 / 客胜并列（90′）") == {"平", "客胜"}
    assert route_rma("平 / 客胜并列（90′）", "主胜", ["1-1", "0-1", "1-0"], "4-0") == RmaRoute.DIRECTION_REWORK
    assert "客胜" in normalize_direction("胶着偏主")
    # V17.4.22：01「胶着」仍三向；对外格子 1-1/2-1 不得扩成三向
    assert atoms_from_scores(["1-1", "2-1"]) == {"平", "主胜"}
    assert public_allowed_set("胶着（1-1 / 2-1）", ["1-1", "2-1"]) == {"平", "主胜"}
    assert public_allowed_set("锁平", ["1-1", "0-0"]) == {"平"}
    assert classify_miss("胶着", {"平", "主胜"}, "客胜") == "A"
    assert classify_miss("胶着偏客", {"客胜", "平"}, "主胜") == "lean_flip"
    assert classify_miss("锁平", {"平"}, "平") is None
    assert public_allowed_set("胶着") == set()
    assert public_allowed_set("胶着偏主") == {"主胜", "平"}
    assert route_rma_public("胶着（1-1 / 2-1）", "客胜", ["1-1", "2-1"], "1-2") == RmaRoute.DIRECTION_REWORK
    assert route_rma_public("锁平", "平", ["1-1", "0-0"], "1-1") == RmaRoute.CLOSED
    # 01 研究入口「胶着」仍三向（不得拿来刷对外）
    assert route_rma("胶着", "客胜", ["1-1", "2-1"], "1-2") == RmaRoute.SCORE_REWORK
    # V17.4.22.2：空槽字面不是允许集；带 01 篮也跳过对外分母
    assert public_allowed_set("空槽") == set()
    assert public_allowed_set("空槽", ["1-2", "0-2"]) == set()
    assert route_rma_public("空槽", "客胜", ["1-2", "0-2"], "0-1") == RmaRoute.SKIP
    assert route_rma_public("空槽", "主胜", [], "1-0") == RmaRoute.SKIP
    # 08-31 夹具：合同内 miss vs 屠杀合同外
    assert score_miss_class("0-1", ["1-2", "0-2", "1-1"]) == "in_contract_pack"
    assert score_miss_class("1-0", ["2-1", "1-1", "0-1"]) == "in_contract_pack"
    assert score_miss_class("0-4", ["1-2", "0-1", "1-1"]) == "contract_out_blowout"
    assert score_miss_class("1-0", ["1-1", "1-0"]) is None
    # V17.4.22.3：主不败不得被「不败」扩成三向
    assert normalize_direction("主不败") == {"主胜", "平"}
    assert normalize_direction("客不败") == {"客胜", "平"}
    assert public_allowed_set("主不败") == {"主胜", "平"}
    assert public_allowed_set("客不败", ["0-1", "1-1"]) == {"客胜", "平"}
    assert route_rma_public("主不败", "主胜", [], "4-2") == RmaRoute.CLOSED
    assert route_rma_public("主不败", "客胜", [], "0-1") == RmaRoute.DIRECTION_REWORK
    assert route_rma_public("主不败", "主胜", ["1-0", "1-1"], "2-0") == RmaRoute.SCORE_REWORK
    assert route_rma_public("客不败", "平", ["1-1", "0-1"], "1-1") == RmaRoute.CLOSED
    assert route_rma("主不败", "客胜", ["1-0", "1-1"], "0-1") == RmaRoute.DIRECTION_REWORK
    print("OK rma_route self-check")


if __name__ == "__main__":
    _self_check()
