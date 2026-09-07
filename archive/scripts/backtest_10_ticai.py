#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
竞彩 2026-08-01 前10场 · V17.4.7 INTEL_FIRST 回测
- 盘口源：澳客竞足指数（非官网 SP，调试用）
- 赛果源：唯彩开奖 / 澳客完场比分
- 方向由【情报】定，Edge 只做出票闸；禁止用赛果反推方向
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]


def load_patches():
    name = "v156_bt"
    spec = importlib.util.spec_from_file_location(name, ROOT / "rules" / "V15.6_patches.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


p = load_patches()


def dewager(oh, od, oa):
    rh, rd, ra = 1 / oh, 1 / od, 1 / oa
    s = rh + rd + ra
    return {"H": rh / s, "D": rd / s, "A": ra / s}, s


def poisson_pda(lh, la, n=5):
    def pois(l, k):
        return math.exp(-l) * l**k / math.factorial(k)

    ph = pd = pa = 0.0
    for i in range(n + 1):
        for j in range(n + 1):
            pr = pois(lh, i) * pois(la, j)
            if i > j:
                ph += pr
            elif i == j:
                pd += pr
            else:
                pa += pr
    t = ph + pd + pa
    return ph / t, pd / t, pa / t


def hc_probs(lh, la, L, n=5):
    def pois(l, k):
        return math.exp(-l) * l**k / math.factorial(k)

    wh = wd = wa = 0.0
    for i in range(n + 1):
        for j in range(n + 1):
            pr = pois(lh, i) * pois(la, j)
            gd = i - j
            if gd > -L:
                wh += pr
            elif gd == -L:
                wd += pr
            else:
                wa += pr
    t = wh + wd + wa
    return wh / t, wd / t, wa / t


@dataclass
class Fixture:
    code: str
    league: str
    home: str
    away: str
    sp: Tuple[float, float, float]
    L: float
    hc_sp: Tuple[float, float, float]
    # 赛前情报（不得含赛果）
    intel: str
    portrait: str
    script_dir: str  # H/D/A — 情报定方向
    script_margin: str
    scores_pick: str
    # λ RAW 点估计（赛前）
    lh: float
    la: float
    lg_half: float
    # 赛果（仅对账）
    score: str
    actual_1x2: str  # H/D/A


# 2026-08-01 竞彩 001–010（完赛）；情报用赛前积分/形态，不写进球结果
FIXTURES: List[Fixture] = [
    Fixture(
        "001",
        "韩K",
        "江原FC",
        "富川FC",
        (1.44, 3.75, 5.95),
        -1,
        (2.60, 3.08, 2.38),
        "赛前：江原积分榜前列主场；富川中下游且休赛后连平连负。市场主胜偏热。",
        "江原主场压迫火力更稳；富川客场进球少、更偏低位。克制：主队控场占优，但非稳过大胜盘。",
        "H",
        "小胜",
        "2-0/1-0/1-1",
        1.55,
        0.90,
        1.25,
        "0:3",
        "A",
    ),
    Fixture(
        "002",
        "韩K",
        "全北现代",
        "首尔FC",
        (2.62, 2.90, 2.48),
        1.0,
        (1.41, 4.05, 5.80),
        "赛前：榜首争夺级对决，首尔积分领先/紧咬，全北主场需分。三项接近胶着。",
        "两队防守组织强、中前场互咬；更像控球消耗战。克制：互咬→平局剧本优先。",
        "D",
        "闷平",
        "0-0/1-1/1-0",
        1.20,
        1.20,
        1.25,
        "0:0",
        "D",
    ),
    Fixture(
        "003",
        "韩K",
        "浦项制铁",
        "金泉尚武",
        (2.29, 2.98, 2.80),
        -1,
        (5.35, 3.88, 1.46),
        "赛前：浦项中游偏上主场；尚武轮换军中游，客场韧性好。主胜不稳。",
        "浦项主场节奏快但近况起伏；尚武定位球/反击威胁。克制：胶着偏主弱优。",
        "H",
        "小胜",
        "1-0/2-1/1-1",
        1.35,
        1.15,
        1.25,
        "0:1",
        "A",
    ),
    Fixture(
        "004",
        "芬超",
        "TPS土尔库",
        "玛丽港",
        (1.39, 4.30, 5.70),
        -1,
        (2.21, 3.55, 2.53),
        "赛前：主队主场热门，客队客场防守偏软。战意主队更明确。",
        "主队主场火力够用；客队客场创造不足。克制：主队压场。",
        "H",
        "中胜",
        "2-0/3-0/2-1",
        1.85,
        0.85,
        1.30,
        "3:0",
        "H",
    ),
    Fixture(
        "005",
        "瑞超",
        "赫根",
        "卡尔马",
        (1.62, 3.85, 3.96),
        -1,
        (2.88, 3.55, 2.00),
        "赛前：赫根榜眼前列但主场连平；卡尔马客场连败求第一分。",
        "赫根控球但不稳收官；卡尔马低位偷反击。克制：主优但不稳→小胜/防平。",
        "H",
        "小胜",
        "2-1/1-0/1-1",
        1.65,
        1.05,
        1.35,
        "1:1",
        "D",
    ),
    Fixture(
        "006",
        "挪超",
        "腓特烈斯塔",
        "桑纳菲尤尔",
        (2.11, 3.24, 2.88),
        -1,
        (4.40, 3.95, 1.54),
        "赛前：两队中下游纠缠，主场略优，三项接近。",
        "主队主场求分；客队客场进球一般。克制：小优势主胜。",
        "H",
        "小胜",
        "1-0/2-1/1-1",
        1.40,
        1.20,
        1.45,
        "1:0",
        "H",
    ),
    Fixture(
        "007",
        "芬超",
        "拉赫蒂",
        "雅罗",
        (1.39, 4.35, 5.55),
        -1,
        (2.52, 2.98, 2.52),
        "赛前：拉赫蒂主场热门；雅罗客场偏弱。",
        "主队主场节奏压制；客队客场失球偏多。克制：主胜。",
        "H",
        "小胜/中胜",
        "2-0/2-1/1-0",
        1.80,
        0.90,
        1.30,
        "2:0",
        "H",
    ),
    Fixture(
        "008",
        "挪超",
        "斯达",
        "维京",
        (5.65, 4.62, 1.36),
        1.0,
        (2.57, 3.80, 2.10),
        "赛前：维京争冠集团火力爆棚；斯达垫底求生。客胜极热。",
        "维京客场推进强；斯达防不住对攻。克制：客队碾压→客胜。",
        "A",
        "中胜/大胜",
        "0-2/0-3/1-3",
        0.85,
        2.10,
        1.45,
        "0:3",
        "A",
    ),
    Fixture(
        "009",
        "芬超",
        "赫尔火花",
        "库普斯",
        (3.22, 3.65, 1.84),
        1.0,
        (1.72, 3.65, 3.65),
        "赛前：库普斯榜首集团客场；火花中游主场偷分难。",
        "客队整体质量更高；主队主场可纠缠但不稳。克制：客胜小胜。",
        "A",
        "小胜",
        "0-1/1-2/0-2",
        1.05,
        1.55,
        1.30,
        "0:1",
        "A",
    ),
    Fixture(
        "010",
        "美职",
        "迈阿密国际",
        "哥伦布机员",
        (1.38, 4.65, 5.30),
        -1,
        (2.06, 4.10, 2.50),
        "赛前：迈阿密主场巨星班底热门；哥伦布防守组织好、客场能磨。",
        "主队进攻上限高；客队反击与定位球威胁。克制：主优但深盘风险→小胜剧本，防平。",
        "H",
        "小胜",
        "2-1/2-0/1-1",
        1.90,
        1.00,
        1.40,
        "2:2",
        "D",
    ),
]


def predict(fx: Fixture) -> Dict:
    # λ'
    lh = 0.65 * fx.lh + 0.35 * fx.lg_half
    la = 0.65 * fx.la + 0.35 * fx.lg_half
    ctx = p.MatchContext(
        lambda_h=lh,
        lambda_a=la,
        handicap_L=fx.L,
        league_name=fx.league,
        away_team=fx.away,
    )
    lh1, la1, lh_sub, la_sub, flags = p.apply_star_factor(ctx)
    ph, pd, pa = poisson_pda(lh1, la1)
    ph, pd, pa, flags = p.run_v156_probability_patches(ph, pd, pa, ctx)
    fair, ov = dewager(*fx.sp)

    # 方向锁死为情报剧本（INTEL_FIRST），不用 argmax 市场
    direction = fx.script_dir
    p_model = {"H": ph, "D": pd, "A": pa}[direction]
    p_fair = fair[direction]
    edge_raw = p_model - p_fair
    edge_eff = edge_raw * 0.60  # RAW Tier2/3

    channel = "不荐"
    star = "☆☆☆☆☆"
    dim = {}
    if edge_eff >= 0.01:
        channel = "胜平负"
        star = "★★☆☆☆"
    else:
        wh, wd, wa = hc_probs(lh_sub, la_sub, fx.L)
        # 让球方向：与剧本同向映射粗略
        # 对 L=-1 主让：主胜剧本→关注让胜；客胜剧本关注让负
        if direction == "H":
            hc_key, p_hc = "H", wh
        elif direction == "A":
            hc_key, p_hc = "A", wa
        else:
            hc_key, p_hc = "D", wd
        fair_hc, _ = dewager(*fx.hc_sp)
        e_raw_hc = p_hc - fair_hc[hc_key]
        e_eff_hc = e_raw_hc * 0.60
        dim = {
            "HC_key": hc_key,
            "Edge_eff_HC%": round(e_eff_hc * 100, 2),
        }
        if e_eff_hc >= 0.03:
            channel = "让球"
            star = "★★☆☆☆"

    market_fav = max(fair.items(), key=lambda kv: kv[1])[0]
    force, flags = p.apply_edge_refine(
        edge_eff, {"H": ph, "D": pd, "A": pa}, fair, market_fav, flags
    )
    # V17.4.7 INTEL_FIRST：【结果预测】锁剧本；Edge_Refine 只影响出票提示，不静默改方向
    final_dir = direction
    ticket_dir = direction
    if force and direction == market_fav:
        # 仅当剧本追着市场热门且主盘负Edge时，出票可改冷门；结果预测仍保留剧本+旁注
        ticket_dir = force
        dim["refine_ticket_only"] = force
        dim["note"] = "Edge_Refine 仅改出票提示，不改【结果预测】"

    hit_dir = final_dir == fx.actual_1x2
    ticket_ok = channel != "不荐"
    # 出票命中按出票方向（含 refine 提示）
    ticket_hit = ticket_ok and (ticket_dir == fx.actual_1x2)

    return {
        "code": fx.code,
        "match": f"{fx.home} vs {fx.away}",
        "league": fx.league,
        "intel": fx.intel,
        "portrait": fx.portrait,
        "script": f"{direction}/{fx.script_margin}/{fx.scores_pick}",
        "λ'": [round(lh, 3), round(la, 3)],
        "P_HDA": [round(ph, 3), round(pd, 3), round(pa, 3)],
        "SP": list(fx.sp),
        "p_fair_dir": round(p_fair, 3),
        "Edge_eff%": round(edge_eff * 100, 2),
        "channel": channel,
        "star": star,
        "dim": dim,
        "patch": p.format_patch_report(flags).split("\n")[0],
        "force": force,
        "final_dir": final_dir,
        "ticket_dir": ticket_dir,
        "market_fav": market_fav,
        "score": fx.score,
        "actual": fx.actual_1x2,
        "hit_dir": hit_dir,
        "ticket_ok": ticket_ok,
        "ticket_hit": ticket_hit,
        "overround": round(ov, 3),
    }


def main():
    rows = [predict(fx) for fx in FIXTURES]
    n = len(rows)
    dir_hits = sum(1 for r in rows if r["hit_dir"])
    tickets = [r for r in rows if r["ticket_ok"]]
    ticket_hits = sum(1 for r in rows if r["ticket_hit"])
    fav_trap = []  # 市场热门（fair最大）≠赛果，且旧习惯会死推热门
    for fx, r in zip(FIXTURES, rows):
        fair, _ = dewager(*fx.sp)
        mkt = max(fair.items(), key=lambda kv: kv[1])[0]
        if mkt != fx.actual_1x2:
            fav_trap.append(
                {
                    "match": r["match"],
                    "market_fav": mkt,
                    "actual": fx.actual_1x2,
                    "our_dir": r["final_dir"],
                    "saved_by_intel": r["final_dir"] == fx.actual_1x2,
                }
            )

    summary = {
        "slate": "竞彩 2026-08-01 001–010",
        "n": n,
        "dir_hit": dir_hits,
        "dir_acc": round(dir_hits / n, 3),
        "ticket_n": len(tickets),
        "ticket_hit": ticket_hits,
        "ticket_acc": round(ticket_hits / len(tickets), 3) if tickets else None,
        "market_upset_n": len(fav_trap),
        "intel_saved_on_upset": sum(1 for x in fav_trap if x["saved_by_intel"]),
        "skill": "football-predict-v17 / V17.4.7 INTEL_FIRST",
        "disclaimer": "澳客指数模拟；非投资建议；λ为赛前点估计",
    }

    out = {"summary": summary, "upsets": fav_trap, "rows": rows}
    out_path = ROOT / "scripts" / "backtest_10_ticai_20260801.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 72)
    print("V17.4.7 INTEL_FIRST · 竞彩10场回测", summary["slate"])
    print(
        f"方向命中 {dir_hits}/{n} = {summary['dir_acc']*100:.1f}%  |  "
        f"出票 {summary['ticket_n']} 场命中 {ticket_hits} = "
        f"{(summary['ticket_acc'] or 0)*100:.1f}%"
    )
    print(
        f"市场冷门局 {summary['market_upset_n']} · 情报救回 "
        f"{summary['intel_saved_on_upset']}"
    )
    print("=" * 72)
    for r in rows:
        mark = "✓" if r["hit_dir"] else "✗"
        tmark = "票✓" if r["ticket_hit"] else ("票—" if not r["ticket_ok"] else "票✗")
        print(
            f"{r['code']} {mark} {tmark} | {r['match']} | 剧本{r['final_dir']} "
            f"市热{r['market_fav']} 赛果{r['actual']} {r['score']} | "
            f"Edge {r['Edge_eff%']}% 通道={r['channel']} | {r['patch']}"
        )
        print(f"   情报: {r['intel'][:60]}…")
    print("\nJSON →", out_path)
    print("OK patches", p.VERSION, p.BOUND_TO)


if __name__ == "__main__":
    main()
