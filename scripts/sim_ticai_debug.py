#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""体彩场次驱动的 V17.4.6 管线调试（SP=SIM，非实盘荐彩）。

赛程锚点：广东体彩公告 26098/26099 期场次（2026-07-28 公示）。
用途：复现双闸门 / 降维 / V15.6 补丁；对比旧 3% 单闸误弃。
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
PATCH_PATH = ROOT / "rules" / "V15.6_patches.py"


def load_patches() -> ModuleType:
    name = "v156_patches"
    spec = importlib.util.spec_from_file_location(name, PATCH_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {PATCH_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclass needs module in sys.modules
    spec.loader.exec_module(mod)
    return mod


p = load_patches()


def dewager(oh: float, od: float, oa: float):
    rh, rd, ra = 1 / oh, 1 / od, 1 / oa
    s = rh + rd + ra
    return {"H": rh / s, "D": rd / s, "A": ra / s}, s


def poisson_pda(lh: float, la: float, n: int = 5):
    def pois(l, k):
        return math.exp(-l) * l**k / math.factorial(k)

    ph = pd = pa = 0.0
    grid = {}
    for i in range(n + 1):
        for j in range(n + 1):
            pr = pois(lh, i) * pois(la, j)
            grid[(i, j)] = pr
            if i > j:
                ph += pr
            elif i == j:
                pd += pr
            else:
                pa += pr
    t = ph + pd + pa
    return ph / t, pd / t, pa / t, grid


def hc_probs(grid, L: float):
    wh = wd = wa = 0.0
    for (i, j), pr in grid.items():
        gd = i - j
        if gd > -L:
            wh += pr
        elif gd == -L:
            wd += pr
        else:
            wa += pr
    t = wh + wd + wa
    return wh / t, wd / t, wa / t


def decide(
    name: str,
    oh: float,
    od: float,
    oa: float,
    lh: float,
    la: float,
    *,
    raw: bool = False,
    lg_half: float = 1.3,
    small_sample: bool = False,
    h2h_away=None,
    h2h_draws=None,
    hc_sp=None,
    L=None,
    home_rank=None,
    league_teams=None,
    home_wins=None,
    away_team=None,
    league_name=None,
    away_def_injuries: int = 0,
    away_attack_intact: bool = True,
    away_win_odds=None,
):
    if raw:
        lh2 = 0.65 * lh + 0.35 * lg_half
        la2 = 0.65 * la + 0.35 * lg_half
        cal = "RAW"
    else:
        lh2, la2 = lh, la
        cal = "npxG"

    ctx = p.MatchContext(
        lambda_h=lh2,
        lambda_a=la2,
        h2h_away_wins_last10=h2h_away,
        h2h_home_draws_last5=h2h_draws,
        home_league_rank=home_rank,
        league_teams=league_teams,
        home_wins=home_wins,
        handicap_L=L,
        away_team=away_team,
        league_name=league_name,
        away_def_injuries=away_def_injuries,
        away_attack_intact=away_attack_intact,
        away_win_odds=away_win_odds,
    )
    lh1, la1, lh_sub, la_sub, flags = p.apply_star_factor(ctx)
    ph, pd, pa, grid = poisson_pda(lh1, la1)
    ph, pd, pa, flags = p.run_v156_probability_patches(ph, pd, pa, ctx)
    fair, ov = dewager(oh, od, oa)
    direction = max([("H", ph), ("D", pd), ("A", pa)], key=lambda x: x[1])[0]
    p_model = {"H": ph, "D": pd, "A": pa}[direction]
    p_fair = fair[direction]
    edge_raw = p_model - p_fair
    edge_eff = edge_raw if not raw else edge_raw * 0.60 * (0.85 if small_sample else 1.0)

    channel = "不荐"
    star = "☆☆☆☆☆"
    dim = {}
    if edge_eff >= 0.01:
        channel = "胜平负"
        star = "★★☆☆☆"
    elif hc_sp is not None and L is not None:
        _, _, _, g = poisson_pda(lh_sub, la_sub)
        wh, wd, wa = hc_probs(g, L)
        hc_dir = max([("H", wh), ("D", wd), ("A", wa)], key=lambda x: x[1])[0]
        fair_hc, _ = dewager(*hc_sp)
        e_raw_hc = {"H": wh, "D": wd, "A": wa}[hc_dir] - fair_hc[hc_dir]
        e_eff_hc = e_raw_hc if not raw else e_raw_hc * 0.60
        e_eff_hc, flags = p.apply_zombie(
            e_eff_hc, home_rank, league_teams, home_wins, L, flags
        )
        dim = {
            "HC_dir": hc_dir,
            "Edge_raw_HC%": round(e_raw_hc * 100, 2),
            "Edge_eff_HC%": round(e_eff_hc * 100, 2),
            "L": L,
        }
        if e_eff_hc >= 0.03:
            channel = "让球"
            star = "★★★☆☆" if e_eff_hc >= 0.05 else "★★☆☆☆"
        else:
            dim["note"] = "降维让球未过3%"
    else:
        dim["note"] = "胜平负<1%且无让球SP→无法降维"

    market_fav = max(fair.items(), key=lambda kv: kv[1])[0]
    force, flags = p.apply_edge_refine(
        edge_eff, {"H": ph, "D": pd, "A": pa}, fair, market_fav, flags
    )
    wrongly_3 = edge_eff >= 0.01 and edge_eff < 0.03
    return {
        "match": name,
        "sp_note": "SIM（调试合成，非官网实时）",
        "caliber": cal,
        "lambda": [round(lh2, 3), round(la2, 3)],
        "P_HDA": [round(ph, 4), round(pd, 4), round(pa, 4)],
        "dir": direction,
        "p_model": round(p_model, 4),
        "p_fair": round(p_fair, 4),
        "Edge_raw%": round(edge_raw * 100, 2),
        "Edge_eff%": round(edge_eff * 100, 2),
        "channel_V1746": channel,
        "star": star,
        "dim": dim,
        "force": force,
        "overround": round(ov, 3),
        "gate_audit": {
            "pass_1pct": edge_eff >= 0.01,
            "pass_old_3pct": edge_eff >= 0.03,
            "wrong_abandon_if_old_3pct": wrongly_3,
        },
        "patch_report": p.format_patch_report(flags),
    }


def main():
    # 场次锚点：
    # 1) 广东体彩胜负彩 26098/26099 公告场次（SP/λ = SIM）
    # 2) 澳客竞足指数（2026-07-31 抓取；非官网 SP，调试对照 DeepSeek 翻车三场）
    cases = [
        decide(
            "26098-1 赫根 vs 卡尔马（瑞超）",
            1.72,
            3.55,
            4.60,
            1.65,
            1.05,
            raw=True,
            lg_half=1.35,
            hc_sp=(2.05, 3.35, 3.20),
            L=-1,
        ),
        decide(
            "26098-3 斯达 vs 维京（挪超）",
            2.85,
            3.35,
            2.35,
            1.20,
            1.45,
            raw=True,
            lg_half=1.40,
            h2h_away=8,
            hc_sp=(1.95, 3.50, 3.40),
            L=0,
            away_team="维京",
            league_name="Eliteserien",
        ),
        decide(
            "26098-5 赫尔辛基火花 vs 库奥皮奥（芬超）",
            3.10,
            3.40,
            2.15,
            1.05,
            1.55,
            raw=True,
            small_sample=True,
            home_rank=12,
            league_teams=12,
            home_wins=1,
            hc_sp=(1.85, 3.45, 3.70),
            L=1.0,
        ),
        decide(
            "26099-1 布鲁马波卡纳 vs 马尔默（瑞超·StarFactor探针）",
            3.40,
            3.50,
            1.95,
            1.15,
            1.70,
            raw=True,
            lg_half=1.40,
            away_team="马尔默",
            league_name="Allsvenskan",
            away_def_injuries=2,
            away_attack_intact=True,
            away_win_odds=1.45,
            hc_sp=(2.15, 3.40, 2.90),
            L=1.0,
        ),
        # DeepSeek 复盘翻车三场（澳客竞足；主盘负Edge→须 Edge_Refine/降维，禁死推热门）
        decide(
            "OKOOO·瓦勒伦加 vs 汉坎",
            1.53,
            3.98,
            4.45,
            1.70,
            1.00,
            raw=True,
            lg_half=1.40,
            hc_sp=(2.60, 3.47, 2.19),
            L=-1,
        ),
        decide(
            "OKOOO·博德闪耀 vs 利勒斯特",
            1.15,
            6.40,
            9.70,
            2.40,
            0.70,
            raw=True,
            lg_half=1.50,
            hc_sp=(2.43, 3.70, 2.24),
            L=-2,
        ),
        decide(
            "OKOOO·纽约城 vs 多伦多FC",
            1.45,
            4.05,
            5.20,
            1.85,
            0.95,
            raw=True,
            lg_half=1.45,
            hc_sp=(2.52, 3.36, 2.30),
            L=-1,
        ),
        decide(
            "教学·样例A npxG 强vs弱",
            1.55,
            3.80,
            5.50,
            1.80,
            0.90,
            raw=False,
        ),
        decide(
            "教学·样例D型 Edge∈[1%,3%) 边界",
            2.10,
            3.30,
            3.40,
            1.10,
            1.60,
            raw=True,
            small_sample=True,
            lg_half=1.30,
            hc_sp=(2.20, 3.30, 2.90),
            L=0,
        ),
        decide(
            "教学·负Edge→Edge_Refine",
            1.45,
            4.20,
            6.50,
            1.10,
            1.70,
            raw=False,
            hc_sp=(2.20, 3.40, 2.70),
            L=-1,
        ),
    ]

    wrong = []
    for c in cases:
        print("=" * 72)
        print(c["match"])
        body = {k: v for k, v in c.items() if k != "patch_report"}
        print(json.dumps(body, ensure_ascii=False, indent=2))
        print(c["patch_report"])
        if c["gate_audit"]["wrong_abandon_if_old_3pct"]:
            wrong.append((c["match"], c["Edge_eff%"]))

    print("\n## GATE CONFLICT: 旧3%单闸会误弃、新1%双闸应介入")
    if not wrong:
        print("(本批无 1%≤Edge_eff<3% 边界场)")
    for m, e in wrong:
        print(f"  WRONG_ABANDON_IF_3pct | {m} | Edge_eff={e}%")

    print(f"\nOK patches={p.VERSION} bound={p.BOUND_TO} cases={len(cases)}")


if __name__ == "__main__":
    main()
