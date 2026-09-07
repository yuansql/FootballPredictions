#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""竞彩 2026-07-18～07-24 · 30场对照回测（训练 skill 用第二窗）。

与 before_0730 / ticai 两窗并列，看 INTEL 胶着带在不同盘口环境下的方差。
情报层=胶着带规则；SP=澳客参考；已剔除 SP 缺失与世界杯表演场；非投资建议。
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
    name = "v156_bt_0718"
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


# 07-24(2)+07-23(7)+07-22(9 剔SP缺失)+07-21(7)+07-20(4)+07-19首1 = 30
# 源：澳客 jingcai 日期页 2026-07-18～07-24
RAW = [
    ("07-24", "201", "芬超", "雅罗", "塞伊奈", 2.95, 3.38, 2.02, 1.0, (1.50, 3.80, 4.80), "2:1"),
    ("07-24", "202", "瑞超", "韦斯特罗", "厄格里特", 1.51, 3.86, 4.80, -1, (2.60, 3.40, 2.20), "2:0"),
    ("07-23", "203", "欧联", "哈马比", "安德莱赫特", 1.70, 3.47, 3.95, -1, (3.40, 3.30, 1.90), "1:1"),
    ("07-23", "204", "欧联", "圣加仑", "本菲卡", 7.95, 5.25, 1.23, 1.0, (3.20, 3.60, 1.85), "2:1"),
    ("07-23", "205", "欧联", "贝西克塔斯", "中日德兰", 2.10, 3.03, 3.10, -1, (4.20, 3.50, 1.60), "1:0"),
    ("07-23", "206", "欧联", "特温特", "费伦茨", 1.38, 4.08, 6.25, -1, (2.20, 3.40, 2.60), "1:2"),
    ("07-23", "207", "欧联", "海杜克", "帕福斯", 1.78, 3.25, 3.85, -1, (3.50, 3.20, 1.85), "2:0"),
    ("07-23", "201", "巴甲", "科林蒂安", "里莫", 1.33, 4.15, 7.30, -1, (2.15, 3.20, 2.80), "3:0"),
    ("07-23", "202", "巴甲", "博塔弗戈", "维多利亚", 1.53, 3.60, 5.05, -1, (2.70, 3.10, 2.30), "0:0"),
    ("07-22", "201", "韩K", "首尔FC", "浦项制铁", 1.60, 3.28, 5.00, -1, (3.00, 3.20, 2.05), "3:1"),
    ("07-22", "202", "韩K", "富川FC", "安养FC", 2.86, 2.72, 2.43, 1.0, (1.45, 3.80, 5.50), "2:3"),
    ("07-22", "203", "韩K", "光州FC", "金泉尚武", 3.65, 2.75, 2.04, 1.0, (1.55, 3.50, 4.80), "1:1"),
    ("07-22", "205", "挪超", "利勒斯特", "维京", 3.13, 3.53, 1.90, 1.0, (1.65, 3.70, 3.90), "1:2"),
    ("07-22", "210", "欧冠", "奥莫尼亚", "阿拉木图凯拉特", 1.54, 3.60, 4.95, -1, (2.70, 3.30, 2.20), "1:0"),
    ("07-22", "206", "美职", "迈阿密国际", "芝加哥火焰", 2.25, 3.60, 2.46, -1, (4.40, 3.80, 1.55), "3:2"),
    ("07-22", "207", "巴甲", "沙佩科", "弗拉门戈", 7.30, 4.60, 1.29, 1.0, (3.00, 3.40, 1.95), "0:4"),
    ("07-22", "208", "巴甲", "圣保罗", "巴拉纳竞技", 1.84, 2.85, 4.25, -1, (3.80, 3.00, 1.85), "1:2"),
    ("07-22", "209", "美职", "洛杉矶FC", "皇家盐湖城", 1.48, 4.30, 4.55, -1, (2.40, 3.50, 2.40), "3:1"),
    ("07-21", "201", "韩K", "济州SK", "江原FC", 4.62, 3.05, 1.71, 1.0, (1.70, 3.20, 4.20), "1:1"),
    ("07-21", "202", "韩K", "全北现代", "大田市民", 1.77, 3.28, 3.85, -1, (3.40, 3.10, 1.90), "0:0"),
    ("07-21", "203", "韩K", "蔚山现代", "仁川联", 2.02, 2.85, 3.53, -1, (4.10, 3.20, 1.70), "1:2"),
    ("07-21", "205", "欧冠", "萨巴赫", "库奥皮奥", 1.42, 4.15, 5.45, -1, (2.30, 3.30, 2.50), "1:0"),
    ("07-21", "206", "欧冠", "奥胡斯", "波兹南", 2.13, 2.80, 3.30, -1, (4.30, 3.20, 1.65), "1:4"),
    ("07-21", "207", "欧冠", "格拉茨风暴", "哈茨", 1.54, 3.80, 4.60, -1, (2.70, 3.40, 2.20), "4:0"),
    ("07-21", "204", "巴甲", "米内罗竞技", "巴伊亚", 1.86, 3.15, 3.65, -1, (3.70, 3.10, 1.85), "1:1"),
    ("07-20", "201", "芬超", "TPS图尔库", "坦山猫", 2.58, 3.20, 2.33, 1.0, (1.50, 3.70, 5.00), "1:3"),
    ("07-20", "202", "芬超", "玛丽港", "拉赫蒂", 5.90, 4.45, 1.36, 1.0, (2.80, 3.40, 2.05), "0:2"),
    ("07-20", "203", "瑞超", "厄格里特", "佐加顿斯", 7.25, 5.60, 1.23, 1.0, (3.10, 3.60, 1.90), "0:0"),
    ("07-20", "204", "瑞超", "卡尔马", "马尔默", 2.50, 3.15, 2.43, -1, (5.00, 3.80, 1.45), "2:2"),
    ("07-19", "201", "韩K", "富川FC", "首尔FC", 5.65, 3.50, 1.50, 1.0, (2.50, 3.30, 2.30), "1:3"),
]

assert len(RAW) == 30, len(RAW)
assert all(r[5] > 0 and r[6] > 0 and r[7] > 0 for r in RAW)


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
        "slate": "竞彩 2026-07-18～07-24（对照窗）",
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
        "disclaimer": "澳客参考指数；情报=胶着带规则；非投资建议；训练对照窗",
    }
    out = {"summary": summary, "rows": rows}
    path = ROOT / "scripts" / "backtest_30_0718_0724.json"
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
    print("【联赛 INTEL】", {lg: f"{b}/{a}" for lg, (a, b, c) in sorted(by_lg.items())})
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
