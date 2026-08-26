#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""比分几何 linter：主/次/防胜平负族正交（V17.4.16 · ADHD）。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from rma_route import parse_score


def outcome_family(score: str) -> str | None:
    parsed = parse_score(score)
    if parsed is None:
        return None
    h, a = parsed
    if h > a:
        return "home"
    if h < a:
        return "away"
    return "draw"


DRAW_TRAP_TAGS = frozenset({"weld_draw", "manage_tie"})


@dataclass
class GeometryIssue:
    code: str
    message: str


def lint_score_geometry(
    structure_tier: str,
    main: str,
    sub: str,
    defense: str,
    *,
   旁: str | None = None,
    direction_tags: Sequence[str] = (),
    defense_abstain: bool = False,
) -> list[GeometryIssue]:
    """structure_tier: high | low"""
    issues: list[GeometryIssue] = []
    tags = set(direction_tags)

    if structure_tier == "low":
        if not defense_abstain and defense.strip() and parse_score(defense):
            issues.append(
                GeometryIssue("low_tier_scored_defense", "低结构场防应显式弃权，不得第三精确分")
            )
        if defense_abstain and not 旁 and not any(t in tags for t in DRAW_TRAP_TAGS):
            issues.append(
                GeometryIssue("abstain_without旁", "防弃权时须保留旁格逃生（纪律#2）")
            )
        return issues

    fams = [outcome_family(x) for x in (main, sub, defense) if parse_score(x)]
    # 仅当三格同族（如 2-1/1-0/3-1 全主胜）才报三联；主+次同族、防异族 = 正常篮
    if len(fams) >= 3 and len(set(fams)) == 1:
        issues.append(GeometryIssue("same_family_triplet", "主/次/防胜平负族须正交，禁止同一故事写三遍"))

    # weld_draw：主/次可双平族，防须异族
    if "weld_draw" in tags and len(fams) >= 3:
        drawish = sum(1 for f in fams if f == "draw")
        if drawish >= 2 and len(set(fams)) >= 2:
            return issues

    main_f = outcome_family(main)
    def_f = outcome_family(defense)
    if main_f and def_f and main_f == def_f and not tags.intersection(DRAW_TRAP_TAGS):
        issues.append(
            GeometryIssue("defense_same_as_main", "防须与主异族，除非 weld_draw/manage_tie 收据授权")
        )

    return issues


def clone_index(baskets: Iterable[tuple[str, str, str]]) -> float:
    """同族三联占比，越低越好。"""
    rows = list(baskets)
    if not rows:
        return 0.0
    bad = 0
    for main, sub, defense in rows:
        fams = [outcome_family(x) for x in (main, sub, defense) if parse_score(x)]
        if len(fams) >= 3 and len(set(fams)) == 1:
            bad += 1
    return bad / len(rows)


def _self_check() -> None:
    # 同族三联：2-1/1-0/3-1 全主胜
    issues = lint_score_geometry("high", "2-1", "1-0", "3-1")
    assert any(i.code == "same_family_triplet" for i in issues)

    # 主+次同族、防异族 = 正常（森林式）
    issues = lint_score_geometry("high", "2-1", "1-0", "1-1")
    assert not any(i.code == "same_family_triplet" for i in issues)

    # weld_draw：1-1/0-0/1-2
    issues = lint_score_geometry("high", "1-1", "0-0", "1-2", direction_tags=["weld_draw"])
    assert not issues

    # 防与主同族（非 draw-trap）
    issues = lint_score_geometry("high", "2-1", "1-1", "1-0", direction_tags=[])
    assert any(i.code == "defense_same_as_main" for i in issues)

    # 低结构 + 弃权无旁
    issues = lint_score_geometry("low", "1-0", "0-0", "弃权", defense_abstain=True)
    assert any(i.code == "abstain_without旁" for i in issues)

    # 正交三格
    issues = lint_score_geometry("high", "2-1", "1-1", "0-1")
    assert not issues

    print("OK score_geometry self-check")


if __name__ == "__main__":
    _self_check()
