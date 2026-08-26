#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RMA 双仓路由：方向返修 vs 比分返修（V17.4.16 · ADHD）。"""
from __future__ import annotations

import re
from enum import Enum
from typing import Iterable, Sequence


class RmaRoute(str, Enum):
    DIRECTION_REWORK = "direction_rework"
    SCORE_REWORK = "score_rework"
    CLOSED = "closed"


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
    t = text.strip()
    out: set[str] = set()
    if "胶着" in t or "并列" in t:
        out.update({"主胜", "平", "客胜"})
        return out
    if "主胜" in t or "主" in t.split("（")[0]:
        out.add("主胜")
    if "客胜" in t or "客" in t.split("（")[0]:
        out.add("客胜")
    if "平" in t:
        out.add("平")
    if "客不败" in t or "不败" in t:
        out.update({"平", "客胜"})
    if "主不败" in t:
        out.update({"主胜", "平"})
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
    print("OK rma_route self-check")


if __name__ == "__main__":
    _self_check()
