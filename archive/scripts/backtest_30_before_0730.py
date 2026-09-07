#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""竞彩 2026-07-25～07-29（严格早于07-30）· 30场分层回测。

训练用途：与 backtest_30_ticai（07-29～08-02）对照，观察窗口方差。
情报层=胶着带规则（非人工全量取证）；SP=澳客参考；非投资建议。
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_patches():
    name = "v156_bt_before0730"
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


def score_1x2(score: str) -> str:
    h, a = map(int, score.replace("：", ":").split(":"))
    if h > a:
        return "H"
    if a > h:
        return "A"
    return "D"


def intel_script(oh, od, oa) -> str:
    fair, _ = dewager(oh, od, oa)
    ranked = sorted(fair.items(), key=lambda kv: kv[1], reverse=True)
    if ranked[0][1] - ranked[1][1] < 0.055:
        return "D"
    if ranked[0][1] < 0.40:
        return "D"
    return ranked[0][0]


def lambda_from_fair(fair, lg_half=1.35):
    lh = 0.65 * (0.75 + 2.0 * fair["H"]) + 0.35 * lg_half
    la = 0.65 * (0.75 + 2.0 * fair["A"]) + 0.35 * lg_half
    return lh, la


def miss_class(direction, market_fav, actual):
    if direction == actual:
        return "HIT"
    if market_fav == actual and direction != actual:
        return "INTEL误伤(市对)"
    if market_fav != actual and direction == actual:
        return "INTEL救回"
    if actual == "D" and market_fav != "D":
        return "热门变平"
    if actual != market_fav and actual != direction:
        return "双错冷门"
    return "其它MISS"


# (date, code, league, home, away, oh,od,oa, L, hc_sp, score)
# 源：澳客竞足日期页；严格 < 2026-07-30
RAW = [
    ("07-29", "001", "欧冠", "阿拉木图凯拉特", "奥莫尼亚", 1.98, 2.92, 3.55, -1, (4.50, 3.32, 1.65), "1:0"),
    ("07-29", "002", "欧冠", "波兹南", "奥胡斯", 1.53, 3.85, 4.62, -1, (2.54, 3.75, 2.13), "0:3"),
    ("07-29", "003", "巴甲", "迈拉索尔", "瑞模", 1.50, 3.80, 5.00, -1, (3.02, 2.92, 2.20), "2:1"),
    ("07-29", "004", "巴甲", "巴西国际", "弗拉门戈", 4.32, 3.52, 1.63, 1.0, (1.97, 3.34, 3.10), "1:1"),
    ("07-29", "005", "巴甲", "弗鲁米嫩塞", "巴伊亚", 1.63, 3.40, 4.50, -1, (3.30, 3.05, 2.01), "0:0"),
    ("07-29", "006", "巴甲", "维多利亚", "帕尔梅拉斯", 4.30, 3.30, 1.69, 1.0, (1.88, 3.30, 3.40), "0:4"),
    ("07-28", "001", "欧冠", "库普斯", "沙巴巴库", 2.80, 3.38, 2.10, 1.0, (1.57, 3.70, 4.50), "0:2"),
    ("07-28", "002", "欧冠", "哈茨", "格拉茨风暴", 1.82, 3.92, 3.08, -1, (3.51, 3.70, 1.74), "0:2"),
    ("07-27", "201", "瑞超", "赫根", "索尔纳", 1.76, 3.50, 3.63, -1, (3.29, 3.70, 1.80), "0:0"),
    ("07-27", "202", "挪超", "罗森博格", "腓特烈斯塔", 1.37, 4.40, 5.80, -1, (2.40, 3.10, 2.56), "4:0"),
    ("07-26", "201", "韩K", "首尔FC", "蔚山现代", 1.65, 3.50, 4.20, -1, (3.15, 3.30, 1.97), "1:3"),
    ("07-26", "202", "韩K", "仁川联", "富川FC", 1.48, 3.55, 5.80, -1, (3.00, 2.85, 2.25), "1:1"),
    ("07-26", "203", "韩K", "光州FC", "济州联", 3.32, 3.00, 2.02, 1.0, (1.59, 3.60, 4.50), "1:2"),
    ("07-26", "204", "韩K", "安养FC", "江原FC", 4.05, 2.83, 1.89, 1.0, (1.70, 3.18, 4.42), "2:1"),
    ("07-26", "205", "瑞超", "布鲁马波", "哈马比", 7.50, 5.30, 1.24, 1.0, (3.18, 3.65, 1.85), "1:1"),
    ("07-26", "206", "瑞超", "天狼星", "哥德堡", 1.31, 4.90, 6.20, -1, (1.95, 3.85, 2.80), "4:1"),
    ("07-26", "207", "芬超", "国际图尔库", "赫尔火花", 1.56, 3.75, 4.50, -1, (3.00, 3.20, 2.07), "1:2"),
    ("07-26", "208", "芬超", "坦山猫", "拉赫蒂", 2.42, 3.30, 2.43, -1, (5.15, 4.42, 1.41), "1:0"),
    ("07-26", "209", "挪超", "布兰", "瓦勒伦加", 1.52, 4.30, 4.20, -1, (2.67, 3.45, 2.15), "2:3"),
    ("07-26", "210", "芬超", "赫尔辛", "TPS土尔库", 1.24, 5.30, 7.50, -1, (1.82, 3.75, 3.20), "1:0"),
    ("07-26", "211", "瑞超", "哥德堡盖斯", "哈尔姆斯塔德", 1.34, 4.50, 6.20, -1, (2.05, 3.80, 2.65), "1:1"),
    ("07-26", "212", "瑞超", "马尔默", "埃尔夫斯堡", 1.84, 3.50, 3.34, -1, (3.56, 3.65, 1.74), "1:2"),
    ("07-26", "213", "挪超", "萨普斯", "汉坎", 1.47, 4.20, 4.75, -1, (2.69, 3.20, 2.25), "1:0"),
    ("07-26", "214", "挪超", "KFUM", "莫尔德", 3.16, 3.30, 1.96, 1.0, (1.66, 3.80, 3.80), "2:4"),
    ("07-26", "215", "挪超", "桑纳菲尤尔", "博德闪耀", 8.00, 6.10, 1.19, 1.0, (3.53, 4.16, 1.65), "0:3"),
    ("07-26", "216", "挪超", "奥勒松", "维京", 5.75, 4.90, 1.33, 1.0, (2.69, 3.68, 2.06), "1:1"),
    ("07-26", "217", "巴甲", "弗拉门戈", "圣保罗", 1.32, 4.40, 6.90, -1, (2.20, 3.17, 2.78), "1:1"),
    ("07-26", "218", "巴甲", "格雷米奥", "弗鲁米嫩塞", 2.79, 2.87, 2.37, 1.0, (1.45, 3.65, 6.05), "1:1"),
    ("07-25", "201", "韩K", "金泉尚武", "大田市民", 2.95, 3.10, 2.14, 1.0, (1.53, 3.60, 5.05), "3:2"),
    ("07-25", "202", "韩K", "浦项制铁", "全北现代", 3.00, 2.78, 2.29, 1.0, (1.47, 3.56, 5.95), "0:2"),
]

assert len(RAW) == 30, len(RAW)


def predict_one(row):
    date, code, league, home, away, oh, od, oa, L, hc_sp, score = row
    fair, ov = dewager(oh, od, oa)
    direction = intel_script(oh, od, oa)
    market_fav = max(fair.items(), key=lambda kv: kv[1])[0]
    actual = score_1x2(score)
    lh, la = lambda_from_fair(fair)
    ctx = p.MatchContext(lambda_h=lh, lambda_a=la, handicap_L=L, league_name=league, away_team=away)
    lh1, la1, lh_sub, la_sub, flags = p.apply_star_factor(ctx)
    ph, pd, pa = poisson_pda(lh1, la1)
    ph, pd, pa, flags = p.run_v156_probability_patches(ph, pd, pa, ctx)
    p_model = {"H": ph, "D": pd, "A": pa}[direction]
    p_fair = fair[direction]
    edge_eff = (p_model - p_fair) * 0.60
    channel = "不荐"
    if edge_eff >= 0.01:
        channel = "胜平负"
    else:
        wh, wd, wa = hc_probs(lh_sub, la_sub, L)
        fair_hc, _ = dewager(*hc_sp)
        e_hc = ({"H": wh, "D": wd, "A": wa}[direction] - fair_hc[direction]) * 0.60
        if e_hc >= 0.03:
            channel = "让球"
    force, flags = p.apply_edge_refine(
        edge_eff, {"H": ph, "D": pd, "A": pa}, fair, market_fav, flags
    )
    return {
        "date": date,
        "code": code,
        "match": f"{home} vs {away}",
        "league": league,
        "script": direction,
        "market_fav": market_fav,
        "actual": actual,
        "score": score,
        "hit": direction == actual,
        "mkt_hit": market_fav == actual,
        "Edge_eff%": round(edge_eff * 100, 2),
        "channel": channel,
        "ticket_ok": channel != "不荐",
        "ticket_hit": channel != "不荐" and direction == actual,
        "mclass": miss_class(direction, market_fav, actual),
        "force": force,
        "overround": round(ov, 3),
        "SP": [oh, od, oa],
    }


def main():
    rows = [predict_one(r) for r in RAW]
    n = len(rows)
    hits = sum(1 for r in rows if r["hit"])
    mkt = sum(1 for r in rows if r["mkt_hit"])
    tickets = [r for r in rows if r["ticket_ok"]]
    th = sum(1 for r in rows if r["ticket_hit"])
    saved = sum(1 for r in rows if r["hit"] and not r["mkt_hit"])
    hurt = sum(1 for r in rows if (not r["hit"]) and r["mkt_hit"])

    by_date = defaultdict(lambda: [0, 0])
    by_lg = defaultdict(lambda: [0, 0, 0])
    for r in rows:
        by_date[r["date"]][0] += 1
        by_date[r["date"]][1] += int(r["hit"])
        by_lg[r["league"]][0] += 1
        by_lg[r["league"]][1] += int(r["hit"])
        by_lg[r["league"]][2] += int(r["mkt_hit"])

    summary = {
        "slate": "竞彩 2026-07-25～07-29（7月30日前）",
        "n": n,
        "dir_hit": hits,
        "dir_acc": round(hits / n, 4),
        "market_hit": mkt,
        "market_acc": round(mkt / n, 4),
        "ticket_n": len(tickets),
        "ticket_hit": th,
        "ticket_acc": round(th / len(tickets), 4) if tickets else None,
        "saved": saved,
        "hurt": hurt,
        "by_date": {d: {"n": a, "intel": b, "acc": round(b / a, 4)} for d, (a, b) in sorted(by_date.items())},
        "by_league": {
            lg: {"n": a, "intel": b, "intel_acc": round(b / a, 4), "market": c, "market_acc": round(c / a, 4)}
            for lg, (a, b, c) in sorted(by_lg.items(), key=lambda kv: -kv[1][0])
        },
        "mclass": dict(Counter(r["mclass"] for r in rows)),
        "skill": "football-predict-v17 / V17.4.8 INTEL_FIRST",
        "disclaimer": "澳客参考指数；情报=胶着带规则；非投资建议；不含07-30及之后",
    }
    out = {"summary": summary, "rows": rows}
    path = ROOT / "scripts" / "backtest_30_before_0730.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 72)
    print("V17.4.8 ·", summary["slate"])
    print(
        f"INTEL {hits}/{n}={summary['dir_acc']*100:.1f}%  |  "
        f"市热 {mkt}/{n}={summary['market_acc']*100:.1f}%  |  "
        f"出票 {len(tickets)} 命中 {th}  |  救回{saved} 误伤{hurt}"
    )
    print("=" * 72)
    print("【按日】", {d: f"{b}/{a}" for d, (a, b) in sorted(by_date.items())})
    print("【失误】", summary["mclass"])
    for r in rows:
        mark = "✓" if r["hit"] else "✗"
        print(
            f"{r['date']}-{r['code']} {mark} | {r['match']} | "
            f"剧本{r['script']} 市{r['market_fav']} 实{r['actual']} {r['score']} | {r['mclass']}"
        )
    print("\nJSON →", path)
    print("OK", getattr(p, "BOUND_TO", p.VERSION))


if __name__ == "__main__":
    main()
