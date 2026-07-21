# -*- coding: utf-8 -*-
"""
V15.6 官方补丁 · 可执行逻辑规范
挂载于 FootballPredictions 底层；未来所有赛事预测强制生效。

Pipeline（与主控对齐）:
  1 原始取证
  2 StarFactor      —— 泊松前调 λ（仅总进球/让球子盘）
  3 泊松 → P_H/D/A
  4 Kryptonite / Jinx —— 重算三项概率
  5 Edge_eff（主盘 + 子盘）
  6 Zombie           —— 仅惩罚让球 Edge
  7 Edge_Refine      —— 主盘 Edge≤-5% 强制冷门
  8 最终预测 / 出票
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

VERSION = "V15.6"
BOUND_TO = "V17.4.6"


# ─── 传统三强白名单（可按联赛扩展）──────────────────────────────────────────
TRADITIONAL_ELITE: Dict[str, Sequence[str]] = {
    "Allsvenskan": ("Malmö FF", "Malmo FF", "马尔默", "AIK", "Djurgården", "Djurgarden", "佐加顿斯"),
    "Veikkausliiga": ("HJK", "Helsinki", "赫尔辛基", "KuPS", "HJK Helsinki"),
    "Eliteserien": ("Bodø/Glimt", "Bodo/Glimt", "博德闪耀", "Rosenborg", "罗森博格", "Molde", "莫尔德"),
}


@dataclass
class PatchFlags:
    kryptonite: bool = False
    zombie: bool = False
    jinx: bool = False
    edge_refine: bool = False
    star_factor: bool = False
    warnings: List[str] = field(default_factory=list)
    force_output: Optional[str] = None
    score_override: Optional[Tuple[str, ...]] = None  # e.g. ("0-0", "1-1")


@dataclass
class MatchContext:
    """本场输入槽；缺失字段 = 对应补丁不触发（禁止臆造）。"""

    # 泊松前
    lambda_h: float
    lambda_a: float
    # 交锋
    h2h_away_wins_last10: Optional[int] = None  # 客队近10次正式交锋胜场
    h2h_home_draws_last5: Optional[int] = None  # 主队主场近5次交锋平局场
    # 排名/战绩
    home_league_rank: Optional[int] = None
    league_teams: Optional[int] = None
    home_wins: Optional[int] = None
    # 盘口：竞彩主队让球线 L；主受让≥1 → L>=+1
    handicap_L: Optional[float] = None
    # 伤停 / 豪门
    away_team: Optional[str] = None
    league_name: Optional[str] = None
    away_def_injuries: int = 0
    away_attack_intact: bool = True
    away_win_odds: Optional[float] = None  # 客胜 SP
    # Edge
    main_edge_eff: Optional[float] = None  # 胜平负方向 Edge_eff（修正后）
    p_model: Optional[Dict[str, float]] = None  # {"H","D","A"}
    p_fair: Optional[Dict[str, float]] = None


# ═══════════════════════════════════════════════════════════════════════════
# Patch 5 · StarFactor（泊松前 · 仅子盘）
# ═══════════════════════════════════════════════════════════════════════════

def is_traditional_elite(team: Optional[str], league: Optional[str]) -> bool:
    if not team:
        return False
    t = team.strip().lower()
    pools: List[str] = []
    if league and league in TRADITIONAL_ELITE:
        pools.extend(TRADITIONAL_ELITE[league])
    else:
        for names in TRADITIONAL_ELITE.values():
            pools.extend(names)
    return any(t == n.lower() or n.lower() in t or t in n.lower() for n in pools)


def apply_star_factor(
    ctx: MatchContext,
    flags: Optional[PatchFlags] = None,
) -> Tuple[float, float, float, float, PatchFlags]:
    """
    客队传统三强 + 后防伤停≥2 + 中前场主力全勤 + 客胜赔≤1.50
    → λ_A * 1.15, λ_H * 1.10
    返回：(λ_H_1x2, λ_A_1x2, λ_H_sub, λ_A_sub, flags)
    主盘口胜平负用未调 λ；总进球/让球子盘用调后 λ。
    """
    flags = flags or PatchFlags()
    lh, la = ctx.lambda_h, ctx.lambda_a
    lh_sub, la_sub = lh, la

    odds_ok = ctx.away_win_odds is not None and ctx.away_win_odds <= 1.50
    if (
        is_traditional_elite(ctx.away_team, ctx.league_name)
        and ctx.away_def_injuries >= 2
        and ctx.away_attack_intact
        and odds_ok
    ):
        la_sub = la * 1.15
        lh_sub = lh * 1.10
        flags.star_factor = True
        flags.warnings.append(
            f"[StarFactor] 豪门残阵对攻溢价：λ_A {la:.3f}→{la_sub:.3f}(+15%)，"
            f"λ_H {lh:.3f}→{lh_sub:.3f}(+10%)；仅子盘生效"
        )
    return lh, la, lh_sub, la_sub, flags


# ═══════════════════════════════════════════════════════════════════════════
# Patch 1 · Kryptonite（泊松后 · Edge 前）
# ═══════════════════════════════════════════════════════════════════════════

def apply_kryptonite(
    p_h: float,
    p_d: float,
    p_a: float,
    h2h_away_wins_last10: Optional[int],
    flags: Optional[PatchFlags] = None,
) -> Tuple[float, float, float, PatchFlags]:
    """
    客队近10次正式交锋胜率 ≥ 80%（≥8胜）→ 拉偏客胜后归一化。
    offset = (win_rate - 0.5) * 0.24  # 最大 ±12%
    """
    flags = flags or PatchFlags()
    if h2h_away_wins_last10 is None or h2h_away_wins_last10 < 8:
        return p_h, p_d, p_a, flags

    win_rate = h2h_away_wins_last10 / 10.0
    if win_rate < 0.80:
        return p_h, p_d, p_a, flags

    offset = (win_rate - 0.5) * 0.24
    p_a_adj = p_a * (1.0 + offset)
    total = p_h + p_d + p_a_adj
    if total <= 0:
        return p_h, p_d, p_a, flags

    flags.kryptonite = True
    flags.warnings.append(
        f"[Kryptonite] 客队 H2H 近10战 {h2h_away_wins_last10}胜 "
        f"(win_rate={win_rate:.0%}) offset={offset:+.3f}"
    )
    return p_h / total, p_d / total, p_a_adj / total, flags


# ═══════════════════════════════════════════════════════════════════════════
# Patch 3 · Jinx（泊松后 · Edge 前）
# ═══════════════════════════════════════════════════════════════════════════

def apply_jinx(
    p_h: float,
    p_d: float,
    p_a: float,
    home_draws_last5: Optional[int],
    flags: Optional[PatchFlags] = None,
) -> Tuple[float, float, float, PatchFlags]:
    """
    两队近5次在主队主场交锋平局率 ≥ 60%（≥3平）
    → P_D = 0.6*P_D_poisson + 0.4*hist；H/A 按比例缩减。
    """
    flags = flags or PatchFlags()
    if home_draws_last5 is None or home_draws_last5 < 3:
        return p_h, p_d, p_a, flags

    draw_rate = home_draws_last5 / 5.0
    if draw_rate < 0.60:
        return p_h, p_d, p_a, flags

    p_d_smoothed = (p_d * 0.6) + (draw_rate * 0.4)
    denom = 1.0 - p_d
    if abs(denom) < 1e-12:
        shrink = 0.0
    else:
        shrink = (1.0 - p_d_smoothed) / denom

    p_h_f = p_h * shrink
    p_a_f = p_a * shrink
    flags.jinx = True
    flags.warnings.append(
        f"[Jinx] 主场近5交锋平局 {home_draws_last5}/5 "
        f"(rate={draw_rate:.0%}) P_D {p_d:.3f}→{p_d_smoothed:.3f}"
    )
    # 若平局成三项最高 → 强制首选平局 + 冷门比分
    if p_d_smoothed >= p_h_f and p_d_smoothed >= p_a_f:
        flags.force_output = "平局首选（Jinx 主场平局专家）"
        flags.score_override = ("0-0", "1-1")
        flags.warnings.append("[Jinx] P_D 为三项最高 → 最终决策平局首选，比分强制含 0-0/1-1")

    return p_h_f, p_d_smoothed, p_a_f, flags


# ═══════════════════════════════════════════════════════════════════════════
# Patch 2 · Zombie（Edge 后 · 仅让球）
# ═══════════════════════════════════════════════════════════════════════════

def apply_zombie(
    edge_eff_handicap: float,
    home_rank: Optional[int],
    league_teams: Optional[int],
    home_wins: Optional[int],
    handicap_L: Optional[float],
    flags: Optional[PatchFlags] = None,
) -> Tuple[float, PatchFlags]:
    """
    主队联赛倒数1或2 + 胜场≤1 + 主队受让≥1（L≥+1）
    → Edge_eff_HC *= 0.60 * 0.65（在 RAW 0.60 之上再叠 0.65）
    调用约定：传入的 edge_eff_handicap 已含 RAW×0.60（若适用）；
    本函数再 ×0.65。若调用方尚未做 RAW 打折，应先打折再传入，
    或使用 apply_zombie_raw_stack 一次叠乘 0.60*0.65。
    """
    flags = flags or PatchFlags()
    if None in (home_rank, league_teams, home_wins, handicap_L):
        return edge_eff_handicap, flags

    bottom2 = home_rank >= (league_teams - 1)  # rank 1-based: N-1, N
    if not (bottom2 and home_wins <= 1 and handicap_L >= 1.0):
        return edge_eff_handicap, flags

    # 规范：在 RAW_GOALS 的 0.60 之上再 ×0.65 → 此处对已打折 Edge 再 ×0.65
    new_edge = edge_eff_handicap * 0.65
    flags.zombie = True
    flags.warnings.append(
        "⚠️ 深盘陷阱预警：垫底队受让不可轻信 "
        f"(rank={home_rank}/{league_teams}, wins={home_wins}, L=+{handicap_L:g}) "
        f"Edge_HC {edge_eff_handicap:+.4f}→{new_edge:+.4f} (×0.65 Zombie)"
    )
    return new_edge, flags


def apply_zombie_raw_stack(
    edge_raw_handicap: float,
    home_rank: Optional[int],
    league_teams: Optional[int],
    home_wins: Optional[int],
    handicap_L: Optional[float],
    flags: Optional[PatchFlags] = None,
) -> Tuple[float, PatchFlags]:
    """一次性：Edge_eff_HC = Edge_raw_HC * 0.60 * 0.65（Zombie 触发时）。"""
    flags = flags or PatchFlags()
    if None in (home_rank, league_teams, home_wins, handicap_L):
        return edge_raw_handicap, flags

    bottom2 = home_rank >= (league_teams - 1)
    if not (bottom2 and home_wins <= 1 and handicap_L >= 1.0):
        return edge_raw_handicap, flags

    new_edge = edge_raw_handicap * 0.60 * 0.65
    flags.zombie = True
    flags.warnings.append(
        "⚠️ 深盘陷阱预警：垫底队受让不可轻信 "
        f"Edge_raw_HC→Edge_eff = ×0.60×0.65 = {new_edge:+.4f}"
    )
    return new_edge, flags


# ═══════════════════════════════════════════════════════════════════════════
# Patch 4 · Edge_Refine（负 Edge 强制冷门）
# ═══════════════════════════════════════════════════════════════════════════

def apply_edge_refine(
    main_edge_eff: float,
    p_model: Dict[str, float],
    p_fair: Dict[str, float],
    market_favorite: str,
    flags: Optional[PatchFlags] = None,
    cold_gate: float = 0.03,
) -> Tuple[Optional[str], PatchFlags]:
    """
    主盘口（胜平负）Edge_eff ≤ -5% → 扫描平局/冷门胜的 Edge；
    若 Edge_cold ≥ 3% → 锁定冷门高赔首选并覆盖比分。
    market_favorite ∈ {"H","D","A"}
    返回 (force_outcome_key or None, flags)
    """
    flags = flags or PatchFlags()
    if main_edge_eff > -0.05:
        return None, flags

    underdog = {"H": "A", "A": "H", "D": "H"}.get(market_favorite, "A")
    candidates = ["D", underdog]
    best_key = None
    best_edge = -1.0
    scanned = []

    for key in candidates:
        if key not in p_model or key not in p_fair:
            continue
        edge_cold = p_model[key] - p_fair[key]
        scanned.append((key, edge_cold))
        if edge_cold >= cold_gate and edge_cold > best_edge:
            best_edge = edge_cold
            best_key = key

    flags.edge_refine = True
    label = {"H": "主胜", "D": "平局", "A": "客胜"}
    if best_key is None:
        flags.warnings.append(
            f"[Edge_Refine] 主盘 Edge_eff={main_edge_eff:.1%}≤-5%，"
            f"冷门扫描未过闸 {[(label.get(k, k), f'{e:+.1%}') for k, e in scanned]}"
        )
        return None, flags

    outcome = label[best_key]
    flags.force_output = f"冷门高赔首选：{outcome}"
    if best_key == "D":
        flags.score_override = ("0-0", "1-1")
    elif best_key == "A":
        flags.score_override = ("0-1", "1-2")
    else:
        flags.score_override = ("1-0", "2-1")
    flags.warnings.append(
        f"[Edge_Refine] 主盘 Edge_eff={main_edge_eff:.1%}≤-5% → "
        f"强制 {flags.force_output} (Edge_cold={best_edge:+.1%})"
    )
    return best_key, flags


# ═══════════════════════════════════════════════════════════════════════════
# Pipeline 编排
# ═══════════════════════════════════════════════════════════════════════════

def run_v156_probability_patches(
    p_h: float,
    p_d: float,
    p_a: float,
    ctx: MatchContext,
) -> Tuple[float, float, float, PatchFlags]:
    """步骤 4：Kryptonite → Jinx（顺序固定）。"""
    flags = PatchFlags()
    p_h, p_d, p_a, flags = apply_kryptonite(
        p_h, p_d, p_a, ctx.h2h_away_wins_last10, flags
    )
    p_h, p_d, p_a, flags = apply_jinx(
        p_h, p_d, p_a, ctx.h2h_home_draws_last5, flags
    )
    return p_h, p_d, p_a, flags


def format_patch_report(flags: PatchFlags) -> str:
    active = []
    if flags.star_factor:
        active.append("StarFactor")
    if flags.kryptonite:
        active.append("Kryptonite")
    if flags.jinx:
        active.append("Jinx")
    if flags.zombie:
        active.append("Zombie")
    if flags.edge_refine:
        active.append("Edge_Refine")
    lines = [f"【V15.6补丁】触发={'+'.join(active) if active else '无'}"]
    for w in flags.warnings:
        lines.append(f"  · {w}")
    if flags.force_output:
        lines.append(f"  · Force_Output={flags.force_output}")
    if flags.score_override:
        lines.append(f"  · Score_Override={'/'.join(flags.score_override)}")
    return "\n".join(lines)


__all__ = [
    "VERSION",
    "BOUND_TO",
    "TRADITIONAL_ELITE",
    "PatchFlags",
    "MatchContext",
    "apply_star_factor",
    "apply_kryptonite",
    "apply_jinx",
    "apply_zombie",
    "apply_zombie_raw_stack",
    "apply_edge_refine",
    "run_v156_probability_patches",
    "format_patch_report",
    "is_traditional_elite",
]
