#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""比分几何 linter：主锚邻格簇 + 进球档（V17.4.17 · ADHD）。

公开/研究三格（主/次/防）须：
  分析 → 方向 → 主锚 → 邻格（最多 3，彼此接近）
异族逃生只允许旁注，不进公开三格。
"""
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


def margin_sign(score: str) -> int | None:
    """+1 home win, 0 draw, -1 away win."""
    fam = outcome_family(score)
    if fam == "home":
        return 1
    if fam == "away":
        return -1
    if fam == "draw":
        return 0
    return None


def goal_total(score: str) -> int | None:
    parsed = parse_score(score)
    if parsed is None:
        return None
    return parsed[0] + parsed[1]


def goal_diff(score: str) -> int | None:
    parsed = parse_score(score)
    if parsed is None:
        return None
    return parsed[0] - parsed[1]


def manhattan(a: str, b: str) -> int | None:
    pa, pb = parse_score(a), parse_score(b)
    if pa is None or pb is None:
        return None
    return abs(pa[0] - pb[0]) + abs(pa[1] - pb[1])


def is_neighbor(
    anchor: str,
    candidate: str,
    *,
    max_manhattan: int = 2,
    max_diff: int = 2,
    max_total_diff: int = 2,
) -> bool:
    """邻格：曼哈顿 ≤2，净胜差 ≤2，总球差 ≤2（允 2-0↔1-1、0-0↔1-1）。"""
    if parse_score(anchor) is None or parse_score(candidate) is None:
        return False
    m = manhattan(anchor, candidate)
    if m is None or m > max_manhattan:
        return False
    da, dc = goal_diff(anchor), goal_diff(candidate)
    ta, tc = goal_total(anchor), goal_total(candidate)
    if da is None or dc is None or ta is None or tc is None:
        return False
    if abs(da - dc) > max_diff:
        return False
    if abs(ta - tc) > max_total_diff:
        return False
    return True


DRAW_TRAP_TAGS = frozenset({"weld_draw", "manage_tie"})


@dataclass
class GeometryIssue:
    code: str
    message: str


def _scored_slots(main: str, sub: str, defense: str) -> list[str]:
    out: list[str] = []
    for s in (main, sub, defense):
        if parse_score(s):
            out.append(s)
    return out


def cluster_ok(
    main: str,
    sub: str,
    defense: str,
    *,
    direction_tags: Sequence[str] = (),
    allow_adjacent_draw: bool = True,
) -> list[GeometryIssue]:
    """公开三格邻域闸：同号（或一格邻近平）+ 相对主锚邻格。"""
    issues: list[GeometryIssue] = []
    tags = set(direction_tags)
    slots = _scored_slots(main, sub, defense)
    if len(slots) < 2:
        return issues

    anchor = main if parse_score(main) else slots[0]
    a_sign = margin_sign(anchor)
    if a_sign is None:
        return issues

    signs = [margin_sign(s) for s in slots]
    win_signs = {s for s in signs if s in (-1, 1)}
    draw_count = sum(1 for s in signs if s == 0)

    if len(win_signs) > 1:
        issues.append(
            GeometryIssue(
                "opposite_sign_in_cluster",
                "公开三格不得混主胜族与客胜族；异族逃生只写旁注",
            )
        )

    if draw_count and a_sign != 0:
        if not allow_adjacent_draw and not tags.intersection(DRAW_TRAP_TAGS):
            issues.append(
                GeometryIssue(
                    "draw_without_receipt",
                    "主胜/客胜锚旁挂平局须 weld_draw/manage_tie 收据，或只交两格邻胜分",
                )
            )
        # 邻近平：1-1 next to 2-1 OK；0-0 next to 2-1 usually fails neighbor

    if a_sign == 0 and win_signs and not tags.intersection(DRAW_TRAP_TAGS):
        # 平锚可带一侧小胜邻格（胶着）
        pass

    for s in slots:
        if s == anchor:
            continue
        if not is_neighbor(anchor, s):
            issues.append(
                GeometryIssue(
                    "not_neighbor_of_anchor",
                    f"{s} 相对主锚 {anchor} 超出邻格（曼哈顿≤2 且净胜/总球差≤2）",
                )
            )

    # 簇内总球跨度：默认 ≤2；draw-trap 可略宽到 3（1-1/0-0/1-2）
    totals = [goal_total(s) for s in slots if goal_total(s) is not None]
    max_spread = 3 if tags.intersection(DRAW_TRAP_TAGS) else 2
    if len(totals) >= 2 and max(totals) - min(totals) > max_spread:
        issues.append(
            GeometryIssue(
                "cluster_total_spread",
                f"三格总进球跨度过大（{min(totals)}–{max(totals)}），须彼此接近",
            )
        )

    return issues


def goals_band_ok(
    scores: Sequence[str],
    band: set[int] | None,
) -> list[GeometryIssue]:
    if not band:
        return []
    issues: list[GeometryIssue] = []
    for s in scores:
        t = goal_total(s)
        if t is None:
            continue
        if t not in band:
            issues.append(
                GeometryIssue(
                    "outside_goals_band",
                    f"{s} 总球 {t} 不在分析进球档 {sorted(band)} 内",
                )
            )
    return issues


def lint_score_geometry(
    structure_tier: str,
    main: str,
    sub: str,
    defense: str,
    *,
    旁: str | None = None,
    direction_tags: Sequence[str] = (),
    defense_abstain: bool = False,
    goals_band: set[int] | None = None,
) -> list[GeometryIssue]:
    """structure_tier: high | low

    V17.4.17：高结构用邻格簇（非异族正交）。
    旁格仍可用于 #2 逃生，但不参与公开簇校验。
    """
    issues: list[GeometryIssue] = []
    tags = set(direction_tags)

    if structure_tier == "low":
        if not defense_abstain and defense.strip() and parse_score(defense):
            issues.append(
                GeometryIssue("low_tier_scored_defense", "低结构场防应显式弃权，不得第三精确分")
            )
        # 主+次须邻格
        if parse_score(main) and parse_score(sub) and not is_neighbor(main, sub):
            issues.append(
                GeometryIssue(
                    "not_neighbor_of_anchor",
                    f"低结构主/次须邻格：{sub} 相对 {main} 过远",
                )
            )
        issues.extend(goals_band_ok([main, sub], goals_band))
        if defense_abstain and not 旁 and not any(t in tags for t in DRAW_TRAP_TAGS):
            issues.append(
                GeometryIssue("abstain_without旁", "低结构防弃权时旁注可留 #2 逃生（研究侧）")
            )
        return issues

    # high：邻格簇（公开 ≤3）
    issues.extend(
        cluster_ok(
            main,
            sub,
            defense,
            direction_tags=direction_tags,
            allow_adjacent_draw=True,
        )
    )
    scored = _scored_slots(main, sub, defense)
    issues.extend(goals_band_ok(scored, goals_band))

    # weld_draw：平族簇可接受双平 + 一邻格小胜
    if "weld_draw" in tags:
        issues = [i for i in issues if i.code != "draw_without_receipt"]

    return issues


def clone_index(baskets: Iterable[tuple[str, str, str]]) -> float:
    """邻格违规占比（越高越差）。旧名保留供周报。"""
    rows = list(baskets)
    if not rows:
        return 0.0
    bad = 0
    for main, sub, defense in rows:
        if lint_score_geometry("high", main, sub, defense):
            bad += 1
    return bad / len(rows)


def cluster_spread(main: str, sub: str, defense: str) -> int | None:
    """相对主锚的最大曼哈顿距离。"""
    if not parse_score(main):
        return None
    spreads = []
    for s in (sub, defense):
        if parse_score(s):
            m = manhattan(main, s)
            if m is not None:
                spreads.append(m)
    return max(spreads) if spreads else 0


def _self_check() -> None:
    # 接近主胜簇 OK
    issues = lint_score_geometry("high", "2-1", "1-0", "2-0")
    assert not issues, issues

    # 邻近平 OK
    issues = lint_score_geometry("high", "2-1", "1-0", "1-1")
    assert not issues, issues

    # 异族逃生进三格 FAIL
    issues = lint_score_geometry("high", "2-1", "1-0", "0-1")
    assert any(i.code == "opposite_sign_in_cluster" for i in issues), issues

    # 散开 FAIL（0-0 与 2-1 过远）
    issues = lint_score_geometry("high", "2-1", "0-0", "3-1")
    assert any(
        i.code in ("not_neighbor_of_anchor", "cluster_total_spread", "opposite_sign_in_cluster")
        for i in issues
    ), issues

    # 进球档
    issues = lint_score_geometry("high", "2-1", "1-1", "2-0", goals_band={2, 3})
    assert not issues, issues
    issues = lint_score_geometry("high", "2-1", "1-1", "2-0", goals_band={1})
    assert any(i.code == "outside_goals_band" for i in issues), issues

    # weld_draw 平簇
    issues = lint_score_geometry("high", "1-1", "0-0", "1-2", direction_tags=["weld_draw"])
    # 1-2 vs 1-1 neighbor? manhattan=1, diff 0 vs -1 =1, totals 2 vs 3 =1 → OK
    # but opposite? draw + away — win_signs={-1}, a_sign=0 → OK path
    assert not any(i.code == "opposite_sign_in_cluster" for i in issues), issues

    # 低结构主次须邻格
    issues = lint_score_geometry("low", "2-1", "0-2", "弃权", defense_abstain=True, 旁="0-1")
    assert any(i.code == "not_neighbor_of_anchor" for i in issues), issues

    issues = lint_score_geometry("low", "2-1", "1-1", "弃权", defense_abstain=True)
    assert any(i.code == "abstain_without旁" for i in issues), issues

    assert is_neighbor("2-1", "1-0")
    assert is_neighbor("2-1", "1-1")
    assert is_neighbor("2-0", "1-1")  # 经典主胜邻平
    # 0-1 相对 2-1 几何上可能相邻，但 lint 须因异号拒
    assert is_neighbor("2-1", "0-1")
    issues = lint_score_geometry("high", "2-1", "1-0", "0-1")
    assert any(i.code == "opposite_sign_in_cluster" for i in issues)
    assert cluster_spread("2-1", "1-0", "1-1") == 2

    print("OK score_geometry self-check (V17.4.17 neighbor cluster)")


if __name__ == "__main__":
    _self_check()
