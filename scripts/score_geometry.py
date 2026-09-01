#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""比分推荐 linter：方向×进球档 · 单格权重 Top3（V17.4.20 · ADHD）。

公开/研究三格（主/次/防）须：
  分析（双方）→ 方向锁 → 进球档 → 【情景路径】→ **每个比分单独计权** → 取权重 Top3 单格
收据过闸且反方向 ±1 球叶 ≥τ → **防格绑定该单格**（非套餐；异族只允许这一格）。
第三与第四单格权重差 <ε → 低结构（01 仍可交权重 #3；禁进 TOP2）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from rma_route import parse_score

# 路径权重和差阈值（权重宜归一到约 1.0）；#3 与 #4 差 <ε → 低结构
TRIO_EPS = 0.15
# 反剧本叶须达此权重才绑进公开 防（弱修辞仍旁注）
COUNTER_TAU = 0.10


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


def score_class(score: str) -> str | None:
    """公开格进球族：shutout | two_goal | open。不是 2-1 镜像 1-2。"""
    parsed = parse_score(score)
    if parsed is None:
        return None
    h, a = parsed
    total = h + a
    if min(h, a) == 0:
        return "shutout"
    if total <= 3:
        return "two_goal"
    return "open"


def same_score_class_pair(a: str, b: str) -> bool:
    ca, cb = score_class(a), score_class(b)
    return ca is not None and ca == cb



DRAW_TRAP_TAGS = frozenset({"weld_draw", "manage_tie"})

# 方向族 × 常见进球档 → 有限候选（分析排序用；lint 只验「在表∪同方向」）
# 平局格可进主胜/客胜方向三格（防平叙事），不靠邻格几何。
CANDIDATE_TABLE: dict[str, dict[frozenset[int], tuple[str, ...]]] = {
    "home": {
        frozenset({1, 2}): ("1-0", "2-0", "2-1", "1-1", "0-0"),
        frozenset({2, 3}): ("2-1", "2-0", "1-0", "3-1", "3-0", "1-1", "2-2"),
        frozenset({3, 4}): ("3-1", "2-1", "3-0", "4-1", "4-0", "2-2", "1-1"),
        frozenset({1}): ("1-0", "0-0", "1-1"),
        frozenset({2}): ("2-0", "2-1", "1-1", "1-0"),
        frozenset({3}): ("2-1", "3-0", "3-1", "1-2"),
    },
    "away": {
        frozenset({1, 2}): ("0-1", "0-2", "1-2", "1-1", "0-0"),
        frozenset({2, 3}): ("1-2", "0-2", "0-1", "1-3", "0-3", "1-1", "2-2"),
        frozenset({3, 4}): ("1-3", "1-2", "0-3", "1-4", "0-4", "2-2", "1-1"),
        frozenset({1}): ("0-1", "0-0", "1-1"),
        frozenset({2}): ("0-2", "1-2", "1-1", "0-1"),
        frozenset({3}): ("1-2", "0-3", "1-3", "2-1"),
    },
    "draw": {
        frozenset({0, 1}): ("0-0", "1-1"),
        frozenset({1, 2}): ("1-1", "0-0", "2-2"),
        frozenset({2, 3}): ("1-1", "2-2", "0-0", "2-1", "1-2"),
        frozenset({2}): ("1-1", "2-2", "0-0"),
        frozenset({0}): ("0-0",),
        frozenset({1}): ("1-1", "0-0"),
    },
}


@dataclass
class GeometryIssue:
    code: str
    message: str


@dataclass(frozen=True)
class PathLeaf:
    path_id: str
    weight: float
    score: str


@dataclass(frozen=True)
class TrioCompareResult:
    """单格权重排序结果（保留名 trio_compare 供 lint 调用）。"""

    ranked_leaves: tuple[tuple[str, float], ...]  # 每个比分单独计权，降序
    best_trio: tuple[str, ...]  # 权重 Top2 或 Top3 **单格**（非组合套餐）
    best_sum: float  # 最高权单格权重
    runner_sum: float  # 第4名单格权重（用于 margin；无则 0）
    margin: float  # 第3与第4单格权重差
    structure_hint: str  # high | low


def _scored_slots(main: str, sub: str, defense: str) -> list[str]:
    out: list[str] = []
    for s in (main, sub, defense):
        if parse_score(s):
            out.append(s)
    return out


def direction_family_from_text(direction: str) -> str | None:
    d = direction.strip()
    if any(x in d for x in ("胶着", "并列")):
        return None  # low structure; caller decides
    if "客胜" in d and "主胜" not in d:
        return "away"
    if "主胜" in d:
        return "home"
    if d in ("平", "平局") or (d.startswith("平") and "防" not in d[:2]):
        return "draw"
    if "平" in d and "客不败" in d:
        return "draw"
    if "客不败" in d or "主不败" in d:
        return None
    return None


def candidates_for(direction_family: str, band: set[int] | None) -> set[str]:
    """有限候选表；无档则退回该方向全部常用分。"""
    rows = CANDIDATE_TABLE.get(direction_family, {})
    if band:
        key = frozenset(band)
        if key in rows:
            return set(rows[key])
        # 模糊：任意与 band 有交集的行并集
        out: set[str] = set()
        for k, vals in rows.items():
            if k & band:
                out.update(vals)
        if out:
            return out
    out = set()
    for vals in rows.values():
        out.update(vals)
    return out


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


def counter_family_from_text(counter_direction: str) -> str | None:
    d = (counter_direction or "").strip()
    if not d or d in ("未触发", "无", "none"):
        return None
    if "客胜" in d:
        return "away"
    if "主胜" in d:
        return "home"
    if "平" in d:
        return "draw"
    return None


def is_one_goal(score: str) -> bool:
    parsed = parse_score(score)
    if parsed is None:
        return False
    return abs(parsed[0] - parsed[1]) == 1


def pick_counter_leaf(
    ranked: Sequence[tuple[str, float]],
    counter_fam: str,
    *,
    tau: float = COUNTER_TAU,
) -> str | None:
    """反方向最高权 ±1 球单格（平则取平格）；weight <τ 视为修辞，不绑。"""
    for score, w in ranked:
        if w < tau:
            continue
        fam = outcome_family(score)
        if fam != counter_fam:
            continue
        if counter_fam in ("home", "away") and not is_one_goal(score):
            continue
        return score
    return None


def pack_with_counter(
    ranked: Sequence[tuple[str, float]],
    counter_score: str,
) -> tuple[str, str, str] | None:
    """主/次 = 非反方向族权重顶二；防 = 绑定反方向单格。"""
    cfam = outcome_family(counter_score)
    pool = [(s, w) for s, w in ranked if s != counter_score and outcome_family(s) != cfam]
    if len(pool) < 2:
        pool = [(s, w) for s, w in ranked if s != counter_score]
    if len(pool) < 2:
        return None
    return (pool[0][0], pool[1][0], counter_score)


def merge_leaf_weights(paths: Sequence[PathLeaf]) -> list[tuple[str, float]]:
    """同终场分权重相加（**每个比分单独**），按权重降序。"""
    acc: dict[str, float] = {}
    for p in paths:
        if not parse_score(p.score):
            continue
        acc[p.score] = acc.get(p.score, 0.0) + float(p.weight)
    return sorted(acc.items(), key=lambda x: (-x[1], x[0]))


def trio_compare(
    paths: Sequence[PathLeaf],
    *,
    eps: float = TRIO_EPS,
) -> TrioCompareResult | None:
    """按单格权重取 Top3：主=第1单格，次=第2，防=第3；第3与第4差 <ε → 低结构。"""
    ranked = merge_leaf_weights(paths)
    if len(ranked) < 2:
        return None

    top1_w = ranked[0][1]
    w3 = ranked[2][1] if len(ranked) >= 3 else 0.0
    w4 = ranked[3][1] if len(ranked) >= 4 else 0.0
    margin = w3 - w4 if len(ranked) >= 4 else w3

    # 不足三格，或第三单格与第四单格权重胶着 → 低结构（仍可交权重 #3）
    hint = "low" if len(ranked) < 3 or margin < eps else "high"
    if len(ranked) >= 3:
        best = (ranked[0][0], ranked[1][0], ranked[2][0])
    else:
        best = (ranked[0][0], ranked[1][0])

    return TrioCompareResult(
        ranked_leaves=tuple(ranked),
        best_trio=best,
        best_sum=top1_w,
        runner_sum=w4,
        margin=margin,
        structure_hint=hint,
    )


def _low_third_ok(
    defense: str,
    paths: Sequence[PathLeaf] | None,
    *,
    eps: float = TRIO_EPS,
) -> bool:
    """低结构第三格合法：必须是权重 #3（含与 #3 同权的并列档）。"""
    if not paths or not parse_score(defense):
        return False
    cmp = trio_compare(paths, eps=eps)
    if cmp is None or len(cmp.ranked_leaves) < 3:
        return False
    w3 = cmp.ranked_leaves[2][1]
    allowed = {s for s, w in cmp.ranked_leaves[2:] if abs(w - w3) < 1e-9}
    return defense.strip() in allowed


def lint_trio_compare(
    main: str,
    sub: str,
    defense: str,
    paths: Sequence[PathLeaf],
    *,
    structure_tier: str,
    defense_abstain: bool = False,
    eps: float = TRIO_EPS,
    counter_direction: str = "",
    weld_family: str | None = None,
) -> list[GeometryIssue]:
    """有路径时：公开格须=单格权重 Top2/Top3；ε 胶着须低结构。

    高结构 + 反方向与焊轴异号：防格须绑 ±1 球 counter 叶（V17.4.20）。
    """
    issues: list[GeometryIssue] = []
    if len(paths) < 2:
        issues.append(
            GeometryIssue(
                "missing_scenario_paths",
                "须 ≥2 条【情景路径】（path_id｜weight｜终场）才能做单格权重排序",
            )
        )
        return issues

    cmp = trio_compare(paths, eps=eps)
    if cmp is None:
        issues.append(
            GeometryIssue("missing_scenario_paths", "路径终场分无法解析，无法做单格排序")
        )
        return issues

    declared = _scored_slots(main, sub, defense if not defense_abstain else "")
    expected = list(cmp.best_trio)
    cfam = counter_family_from_text(counter_direction)
    opposite = (
        weld_family in ("home", "away")
        and cfam in ("home", "away")
        and cfam != weld_family
    )
    counter_score = (
        pick_counter_leaf(cmp.ranked_leaves, cfam) if opposite and cfam else None
    )

    if (
        structure_tier == "high"
        and opposite
        and not defense_abstain
        and not counter_score
    ):
        issues.append(
            GeometryIssue(
                "missing_counter_bind",
                f"收据 counter={counter_direction} 须有 ≥τ={COUNTER_TAU} 的 ±1 球情景叶"
                "并占用公开 防格（真爆冷最像几分）；弱叶仍旁注",
            )
        )

    if counter_score and structure_tier == "high" and not defense_abstain:
        packed = pack_with_counter(cmp.ranked_leaves, counter_score)
        if packed:
            expected = list(packed)
            if len(declared) >= 3:
                if declared[2] != counter_score:
                    issues.append(
                        GeometryIssue(
                            "counter_bind_mismatch",
                            f"防格须绑反方向单格 {counter_score}（现 {declared[2]}）；"
                            "02 可写「真爆冷最像该分」",
                        )
                    )
                if declared[0] != expected[0] or declared[1] != expected[1]:
                    issues.append(
                        GeometryIssue(
                            "trio_pick_mismatch",
                            f"主/次须为焊轴族顶二 {expected[0]}/{expected[1]} "
                            f"（现 {declared[0]}/{declared[1]}）",
                        )
                    )
            elif len(declared) < 3:
                issues.append(
                    GeometryIssue(
                        "counter_bind_mismatch",
                        f"高结构收据场防格须交反方向 {counter_score}，不得弃权",
                    )
                )
        return issues

    if cmp.structure_hint == "low":
        if structure_tier == "high" and parse_score(defense) and not defense_abstain:
            issues.append(
                GeometryIssue(
                    "trio_margin_epsilon",
                    f"第3与第4单格权重差 {cmp.margin:.3f} <ε={eps}，"
                    f"禁止硬交三格；须降为低结构（主={expected[0]} 次={expected[1]}，防弃权）",
                )
            )
        if len(declared) >= 2 and len(cmp.ranked_leaves) >= 2:
            top_score = cmp.ranked_leaves[0][0]
            second_w = cmp.ranked_leaves[1][1]
            allowed_sub = {
                s for s, w in cmp.ranked_leaves[1:] if abs(w - second_w) < 1e-9
            }
            if declared[0] != top_score or declared[1] not in allowed_sub:
                issues.append(
                    GeometryIssue(
                        "trio_pick_mismatch",
                        f"公开主/次={declared[0]}/{declared[1]} "
                        f"≠ 单格权重 Top2 {top_score}+{{{','.join(sorted(allowed_sub))}}} "
                        f"(margin={cmp.margin:.3f})",
                    )
                )
        return issues

    # high：三格 = 单格权重 Top3（主=第1，次=第2，防=第3）
    if len(declared) < 3:
        issues.append(
            GeometryIssue(
                "trio_pick_mismatch",
                f"高结构须交三格=单格权重 Top3 {'/'.join(expected)}；缺格",
            )
        )
        return issues

    exp_main, exp_sub, exp_def = expected[0], expected[1], expected[2]
    if declared != [exp_main, exp_sub, exp_def]:
        issues.append(
            GeometryIssue(
                "trio_pick_mismatch",
                f"公开 {'/'.join(declared)} ≠ 单格 Top3 {'/'.join(expected)} "
                f"(#1={cmp.best_sum:.3f} #3-#4 margin={cmp.margin:.3f})；"
                "每个比分单独计权，禁止套餐/组合任选",
            )
        )
    return issues


def lint_anti_echo(
    paths: Sequence[PathLeaf],
    main: str,
    sub: str,
    defense: str,
    *,
    structure_tier: str,
    counter_bound: str | None = None,
) -> list[GeometryIssue]:
    """同链全是同一胜族、公开三格无平/反方向 → 双计回声。"""
    if structure_tier != "high" or len(paths) < 2:
        return []
    fams = {outcome_family(p.score) for p in paths if parse_score(p.score)}
    win_fams = fams & {"home", "away"}
    if len(win_fams) != 1 or "draw" in fams:
        return []
    slots = _scored_slots(main, sub, defense)
    slot_fams = {outcome_family(s) for s in slots}
    if "draw" in slot_fams:
        return []
    if counter_bound and counter_bound in slots:
        return []
    return [
        GeometryIssue(
            "anti_echo_no_hedge",
            "情景叶与公开格同一胜族、无平防/反方向格：同链双计。"
            "防须换 1-1 或收据 ±1 球反方向（异链路）",
        )
    ]


def lint_top3_rank(
    main: str,
    sub: str,
    defense: str,
    *,
    direction_family: str | None,
    goals_band: set[int] | None = None,
    direction_tags: Sequence[str] = (),
    allow_draw_hedge: bool = True,
    counter_defense: str | None = None,
) -> list[GeometryIssue]:
    """公开三格：同方向（可含一格平防）+ 总球∈档 + 宜在候选表内。

    不查曼哈顿邻格。混主客胜族 → fail。
    收据绑定的 ±1 球防格可豁免异族（仅该一格）。
    """
    issues: list[GeometryIssue] = []
    tags = set(direction_tags)
    slots = _scored_slots(main, sub, defense)
    if len(slots) < 2:
        return issues

    signs = [margin_sign(s) for s in slots]
    win_signs = {s for s in signs if s in (-1, 1)}
    if len(win_signs) > 1:
        waived = False
        if counter_defense and counter_defense in slots and is_one_goal(counter_defense):
            others = [s for s in slots if s != counter_defense]
            other_win = {margin_sign(s) for s in others} & {-1, 1}
            if len(other_win) <= 1:
                waived = True
        if not waived:
            issues.append(
                GeometryIssue(
                    "opposite_sign_in_cluster",
                    "公开三格不得混主胜族与客胜族；异族逃生只写旁注"
                    "（收据 ±1 球防格除外）",
                )
            )

    # 推断方向族
    fam = direction_family
    if fam is None and len(win_signs) == 1:
        fam = "home" if 1 in win_signs else "away"
    if fam is None and all(s == 0 for s in signs if s is not None):
        fam = "draw"

    if fam in ("home", "away") and allow_draw_hedge:
        pass

    if fam and "weld_draw" not in tags and "manage_tie" not in tags:
        for s in slots:
            if s == counter_defense:
                continue
            sf = outcome_family(s)
            if sf is None:
                continue
            if fam in ("home", "away") and sf not in (fam, "draw"):
                issues.append(
                    GeometryIssue(
                        "off_direction_score",
                        f"{s} 不在锁死方向族 {fam}（平格防平除外）",
                    )
                )
            if fam == "draw" and sf not in ("draw", "home", "away"):
                pass

    issues.extend(goals_band_ok(slots, goals_band))

    if fam in CANDIDATE_TABLE and goals_band:
        allowed = candidates_for(fam, goals_band)
        hedge = {"1-1", "0-0", "2-2"} if fam in ("home", "away") else set()
        if counter_defense:
            hedge = set(hedge) | {counter_defense}
        for s in slots:
            if s not in allowed and s not in hedge:
                if outcome_family(s) in (fam, "draw") or (
                    fam == "draw" and outcome_family(s) in ("home", "away", "draw")
                ):
                    issues.append(
                        GeometryIssue(
                            "outside_candidate_table",
                            f"{s} 不在方向={fam}×进球档={sorted(goals_band)} 候选表；"
                            "须有双方分析理由或改旁注",
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
    direction_text: str = "",
    paths: Sequence[PathLeaf] | None = None,
    require_paths: bool = False,
    eps: float = TRIO_EPS,
    counter_direction: str = "",
) -> list[GeometryIssue]:
    """structure_tier: high | low

    V17.4.20：单格 Top3 + 收据 ±1 球防格绑定 + 同链反回声。
    """
    issues: list[GeometryIssue] = []
    tags = set(direction_tags)
    fam = direction_family_from_text(direction_text) if direction_text else None
    cfam = counter_family_from_text(counter_direction)
    counter_score = None
    if paths and fam and cfam and fam != cfam and cfam in ("home", "away"):
        ranked = merge_leaf_weights(paths)
        counter_score = pick_counter_leaf(ranked, cfam)

    if paths:
        issues.extend(
            lint_trio_compare(
                main,
                sub,
                defense,
                paths,
                structure_tier=structure_tier,
                defense_abstain=defense_abstain,
                eps=eps,
                counter_direction=counter_direction,
                weld_family=fam,
            )
        )
        issues.extend(
            lint_anti_echo(
                paths,
                main,
                sub,
                defense,
                structure_tier=structure_tier,
                counter_bound=counter_score,
            )
        )
    elif require_paths:
        issues.append(
            GeometryIssue(
                "missing_scenario_paths",
                "高结构须写【情景路径】并做单格权重排序；禁止无路径任选",
            )
        )

    if structure_tier == "low":
        third_ok = _low_third_ok(defense, paths, eps=eps)
        if (
            not defense_abstain
            and defense.strip()
            and parse_score(defense)
            and not third_ok
        ):
            issues.append(
                GeometryIssue(
                    "low_tier_scored_defense",
                    "低结构第三格须是权重 #3（或弃权），不得发明精确分",
                )
            )
        issues_dir: list[GeometryIssue] = []
        scored = _scored_slots(
            main, sub, defense if (not defense_abstain and third_ok) else ""
        )
        if len(scored) >= 2:
            signs = {margin_sign(s) for s in scored}
            win = signs & {-1, 1}
            if len(win) > 1:
                issues_dir.append(
                    GeometryIssue(
                        "opposite_sign_in_cluster",
                        "公开三格不得混主胜族与客胜族；异族逃生只写旁注",
                    )
                )
        band_slots = [main, sub]
        if not defense_abstain and third_ok:
            band_slots.append(defense)
        issues_dir.extend(goals_band_ok(band_slots, goals_band))
        if defense_abstain and not 旁 and not any(t in tags for t in DRAW_TRAP_TAGS):
            issues_dir.append(
                GeometryIssue("abstain_without旁", "低结构防弃权时旁注可留 #2 逃生（研究侧）")
            )
        issues.extend(issues_dir)
        return issues

    issues.extend(
        lint_top3_rank(
            main,
            sub,
            defense,
            direction_family=fam,
            goals_band=goals_band,
            direction_tags=direction_tags,
            counter_defense=counter_score if defense == counter_score else None,
        )
    )
    if tags.intersection(DRAW_TRAP_TAGS):
        issues = [i for i in issues if i.code != "outside_candidate_table"]
    return issues


def clone_index(baskets: Iterable[tuple[str, str, str]]) -> float:
    """公开三格违规占比（越高越差）。"""
    rows = list(baskets)
    if not rows:
        return 0.0
    bad = 0
    for main, sub, defense in rows:
        if lint_score_geometry("high", main, sub, defense, goals_band={2, 3}, direction_text="主胜"):
            bad += 1
    return bad / len(rows)


def _self_check() -> None:
    # 形状闸：两套都能过方向×档（≠同等推荐）
    issues = lint_score_geometry(
        "high", "2-1", "1-0", "1-1", goals_band={1, 2, 3}, direction_text="主胜"
    )
    assert not any(
        i.code in ("opposite_sign_in_cluster", "outside_goals_band") for i in issues
    ), issues

    issues = lint_score_geometry(
        "high", "2-1", "2-0", "1-1", goals_band={2, 3}, direction_text="主胜"
    )
    assert not any(i.code == "opposite_sign_in_cluster" for i in issues), issues
    assert not any(i.code == "outside_goals_band" for i in issues), issues

    # 单格 Top3：2-1>2-0=1-1>1-0 → 2-1/2-0/1-1（1-0 排第四，不进三格）
    paths_win_20 = [
        PathLeaf("A", 0.40, "2-1"),
        PathLeaf("B", 0.25, "2-0"),
        PathLeaf("C", 0.25, "1-1"),
        PathLeaf("D", 0.10, "1-0"),
    ]
    cmp = trio_compare(paths_win_20, eps=TRIO_EPS)
    assert cmp is not None
    assert cmp.best_trio == ("2-1", "1-1", "2-0"), cmp
    assert cmp.structure_hint == "high", cmp
    issues = lint_score_geometry(
        "high",
        "2-1",
        "1-1",
        "2-0",
        goals_band={2, 3},
        direction_text="主胜",
        paths=paths_win_20,
    )
    assert not any(i.code == "trio_pick_mismatch" for i in issues), issues
    # 1-0 权重不够进 Top3
    issues = lint_score_geometry(
        "high",
        "2-1",
        "1-0",
        "1-1",
        goals_band={1, 2, 3},
        direction_text="主胜",
        paths=paths_win_20,
    )
    assert any(i.code == "trio_pick_mismatch" for i in issues), issues

    # 1-0 单格权重高于 2-0 → Top3 含 1-0 不含 1-1（非套餐二选一）
    paths_10_over_20 = [
        PathLeaf("A", 0.40, "2-1"),
        PathLeaf("B", 0.30, "1-0"),
        PathLeaf("C", 0.20, "2-0"),
        PathLeaf("D", 0.05, "1-1"),
    ]
    cmp = trio_compare(paths_10_over_20, eps=TRIO_EPS)
    assert cmp is not None and cmp.best_trio == ("2-1", "1-0", "2-0"), cmp

    # ε 胶着 → 须低结构
    paths_tie = [
        PathLeaf("A", 0.34, "2-1"),
        PathLeaf("B", 0.22, "2-0"),
        PathLeaf("C", 0.22, "1-0"),
        PathLeaf("D", 0.22, "1-1"),
    ]
    cmp = trio_compare(paths_tie, eps=0.15)
    assert cmp is not None and cmp.structure_hint == "low", cmp
    issues = lint_score_geometry(
        "high",
        "2-1",
        "2-0",
        "1-1",
        goals_band={1, 2, 3},
        direction_text="主胜",
        paths=paths_tie,
        eps=0.15,
    )
    assert any(i.code == "trio_margin_epsilon" for i in issues), issues
    issues = lint_score_geometry(
        "low",
        "2-1",
        "2-0",
        "弃权",
        defense_abstain=True,
        goals_band={2, 3},
        direction_text="胶着偏主",
        paths=paths_tie,
        eps=0.15,
        旁="0-1",
    )
    assert not any(i.code == "trio_margin_epsilon" for i in issues), issues
    # V17.4.22.2：低结构可交权重 #3（并列第三档按名字取 1-0）；弃权仍合法
    issues = lint_score_geometry(
        "low",
        "2-1",
        "1-0",
        "1-1",
        goals_band={1, 2, 3},
        direction_text="胶着偏主",
        paths=paths_tie,
        eps=0.15,
    )
    assert not any(i.code == "low_tier_scored_defense" for i in issues), issues
    issues = lint_score_geometry(
        "low",
        "2-1",
        "1-0",
        "3-0",
        goals_band={1, 2, 3},
        direction_text="胶着偏主",
        paths=paths_tie,
        eps=0.15,
    )
    assert any(i.code == "low_tier_scored_defense" for i in issues), issues

    # 异族逃生进三格 FAIL
    issues = lint_score_geometry(
        "high", "2-1", "1-0", "0-1", goals_band={1, 2, 3}, direction_text="主胜"
    )
    assert any(i.code == "opposite_sign_in_cluster" for i in issues), issues

    # 进球档
    issues = lint_score_geometry(
        "high", "2-1", "1-0", "1-1", goals_band={2, 3}, direction_text="主胜"
    )
    assert any(i.code == "outside_goals_band" for i in issues), issues

    issues = lint_score_geometry(
        "high", "2-1", "2-0", "1-1", goals_band={2, 3}, direction_text="主胜"
    )
    assert not any(i.code == "outside_goals_band" for i in issues), issues

    # weld_draw
    issues = lint_score_geometry(
        "high",
        "1-1",
        "0-0",
        "1-2",
        direction_tags=["weld_draw"],
        goals_band={0, 1, 2, 3},
        direction_text="平",
    )
    assert not any(i.code == "opposite_sign_in_cluster" for i in issues), issues

    # 低结构
    issues = lint_score_geometry(
        "low",
        "2-1",
        "1-1",
        "弃权",
        defense_abstain=True,
        goals_band={2, 3},
        direction_text="胶着偏主",
    )
    assert not any(i.code == "not_neighbor_of_anchor" for i in issues), issues
    assert any(i.code == "abstain_without旁" for i in issues), issues

    issues = lint_score_geometry(
        "high", "2-1", "3-0", "1-1", goals_band={2, 3}, direction_text="主胜"
    )
    assert not any(i.code == "not_neighbor_of_anchor" for i in issues), issues
    assert not any(i.code == "opposite_sign_in_cluster" for i in issues), issues

    # V17.4.20：收据 + 0-1 叶 → 防格绑定；异族豁免
    paths_counter = [
        PathLeaf("A", 0.40, "2-1"),
        PathLeaf("B", 0.25, "2-0"),
        PathLeaf("C", 0.20, "1-1"),
        PathLeaf("D", 0.15, "0-1"),
    ]
    assert pick_counter_leaf(merge_leaf_weights(paths_counter), "away") == "0-1"
    issues = lint_score_geometry(
        "high",
        "2-1",
        "2-0",
        "0-1",
        goals_band={1, 2, 3},
        direction_text="主胜",
        paths=paths_counter,
        counter_direction="客胜",
    )
    assert not any(i.code == "opposite_sign_in_cluster" for i in issues), issues
    assert not any(i.code == "counter_bind_mismatch" for i in issues), issues
    issues = lint_score_geometry(
        "high",
        "2-1",
        "2-0",
        "1-1",
        goals_band={1, 2, 3},
        direction_text="主胜",
        paths=paths_counter,
        counter_direction="客胜",
    )
    assert any(i.code == "counter_bind_mismatch" for i in issues), issues

    # 同链无对冲
    paths_echo = [
        PathLeaf("A", 0.40, "2-1"),
        PathLeaf("B", 0.30, "2-0"),
        PathLeaf("C", 0.20, "3-0"),
        PathLeaf("D", 0.10, "1-0"),
    ]
    issues = lint_score_geometry(
        "high",
        "2-1",
        "2-0",
        "3-0",
        goals_band={2, 3},
        direction_text="主胜",
        paths=paths_echo,
    )
    assert any(i.code == "anti_echo_no_hedge" for i in issues), issues

    # V17.4.22 格子族：1-1/2-1 同族；1-1/0-0 与 2-1/1-0 跨族
    assert score_class("1-1") == "two_goal"
    assert score_class("2-1") == "two_goal"
    assert score_class("0-0") == "shutout"
    assert score_class("1-0") == "shutout"
    assert score_class("2-2") == "open"
    assert same_score_class_pair("1-1", "2-1")
    assert not same_score_class_pair("1-1", "0-0")
    assert not same_score_class_pair("2-1", "1-0")

    print("OK score_geometry self-check (V17.4.22.2 低结构可交权重 #3)")


if __name__ == "__main__":
    _self_check()
