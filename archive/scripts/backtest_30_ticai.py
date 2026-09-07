#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""竞彩最近30场 · V17.4.7 INTEL_FIRST 回测（澳客SP + 唯彩/澳客赛果）。"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_patches():
    name = "v156_bt30"
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
    """赛前情报代理：胶着带优先，否则取去水后最强项（非偷看赛果）。"""
    fair, _ = dewager(oh, od, oa)
    ranked = sorted(fair.items(), key=lambda kv: kv[1], reverse=True)
    # 三项胶着 / 前两名极近 → 平局剧本
    if ranked[0][1] - ranked[1][1] < 0.055:
        return "D"
    if ranked[0][1] < 0.40:
        return "D"
    return ranked[0][0]


def lambda_from_fair(fair, lg_half=1.35):
    lh = 0.65 * (0.75 + 2.0 * fair["H"]) + 0.35 * lg_half
    la = 0.65 * (0.75 + 2.0 * fair["A"]) + 0.35 * lg_half
    return lh, la


# (date, code, league, home, away, oh,od,oa, L, hc_sp, score)
# 源：澳客竞足 + 唯彩开奖；SP=停售前参考指数
RAW = [
    # ---- 2026-08-02 ----
    ("08-02", "K001", "韩K", "蔚山现代", "安养FC", 2.02, 3.40, 2.94, -1, (4.15, 3.80, 1.60), "3:1"),
    ("08-02", "K002", "韩K", "济州联", "仁川联", 2.80, 2.75, 2.45, 1.0, (1.41, 3.95, 6.00), "3:3"),
    ("08-02", "K003", "韩K", "大田市民", "光州FC", 1.44, 3.85, 5.70, -1, (2.50, 3.20, 2.40), "2:0"),
    # ---- 2026-08-01 (16) ----
    ("08-01", "001", "韩K", "江原FC", "富川FC", 1.44, 3.75, 5.95, -1, (2.60, 3.08, 2.38), "0:3"),
    ("08-01", "002", "韩K", "全北现代", "首尔FC", 2.62, 2.90, 2.48, 1.0, (1.41, 4.05, 5.80), "0:0"),
    ("08-01", "003", "韩K", "浦项制铁", "金泉尚武", 2.29, 2.98, 2.80, -1, (5.35, 3.88, 1.46), "0:1"),
    ("08-01", "004", "芬超", "TPS土尔库", "玛丽港", 1.39, 4.30, 5.70, -1, (2.21, 3.55, 2.53), "3:0"),
    ("08-01", "005", "瑞超", "赫根", "卡尔马", 1.62, 3.85, 3.96, -1, (2.88, 3.55, 2.00), "1:1"),
    ("08-01", "006", "挪超", "腓特烈斯塔", "桑纳菲尤尔", 2.11, 3.24, 2.88, -1, (4.40, 3.95, 1.54), "1:0"),
    ("08-01", "007", "芬超", "拉赫蒂", "雅罗", 1.39, 4.35, 5.55, -1, (2.52, 2.98, 2.52), "2:0"),
    ("08-01", "008", "挪超", "斯达", "维京", 5.65, 4.62, 1.36, 1.0, (2.57, 3.80, 2.10), "0:3"),
    ("08-01", "009", "芬超", "赫尔火花", "库普斯", 3.22, 3.65, 1.84, 1.0, (1.72, 3.65, 3.65), "0:1"),
    ("08-01", "010", "美职", "迈阿密国际", "哥伦布机员", 1.38, 4.65, 5.30, -1, (2.06, 4.10, 2.50), "2:2"),
    ("08-01", "011", "美职", "温哥华白帽", "洛杉矶FC", 1.91, 3.65, 3.02, -1, (3.48, 4.05, 1.68), "1:1"),
    ("08-01", "012", "巴西杯", "桑托斯", "瑞模", 1.42, 3.82, 6.10, -1, (2.49, 3.15, 2.44), "0:0"),
    ("08-01", "013", "美职", "芝加哥火焰", "夏洛特FC", 1.37, 4.50, 5.65, -1, (2.20, 3.45, 2.60), "2:1"),
    ("08-01", "014", "美职", "圣路易斯市", "皇家盐湖城", 1.88, 3.75, 3.02, -1, (3.65, 3.80, 1.69), "1:1"),
    ("08-01", "015", "美职", "洛杉矶银河", "达拉斯FC", 2.21, 3.35, 2.64, -1, (4.40, 4.16, 1.51), "0:0"),
    ("08-01", "016", "美职", "波特兰伐木工", "西雅图海湾人", 1.91, 3.70, 2.98, -1, (3.60, 3.95, 1.67), "2:1"),
    # ---- 2026-07-31 ----
    ("07-31", "N001", "挪超", "瓦勒伦加", "汉坎", 1.53, 3.98, 4.45, -1, (2.60, 3.47, 2.19), "0:3"),
    ("07-31", "N002", "挪超", "博德闪耀", "利勒斯特", 1.15, 6.40, 9.70, -2, (2.43, 3.70, 2.24), "4:0"),
    ("07-31", "M001", "美职", "纽约城", "多伦多FC", 1.45, 4.05, 5.20, -1, (2.52, 3.36, 2.30), "1:1"),
    # ---- 2026-07-30 ----
    ("07-30", "E001", "欧联", "中日德兰", "贝西克塔斯", 1.73, 3.75, 3.52, -1, (3.58, 3.30, 1.83), "0:2"),
    ("07-30", "E002", "欧联", "AEP帕福斯", "海杜克", 1.71, 3.65, 3.69, -1, (3.40, 3.36, 1.86), "2:0"),
    ("07-30", "E003", "欧联", "安德莱赫特", "哈马比", 2.11, 3.25, 2.88, -1, (4.55, 3.85, 1.54), "3:1"),
    ("07-30", "E004", "欧联", "费伦茨", "特温特", 2.58, 3.50, 2.19, 1.0, (1.50, 4.10, 4.56), "2:2"),
    ("07-30", "E005", "欧联", "本菲卡", "圣加仑", 1.12, 8.22, 16.26, -2, (2.05, 3.55, 2.78), "5:0"),
    ("07-30", "B001", "巴甲", "科林蒂安", "巴拉纳竞技", 1.80, 2.95, 4.25, -1, (4.06, 3.05, 1.80), "0:0"),
    # ---- 2026-07-29 ----
    ("07-29", "C001", "欧冠", "波兹南", "奥胡斯", 1.53, 3.85, 4.62, -1, (2.54, 3.75, 2.13), "0:3"),
    ("07-29", "B002", "巴甲", "维多利亚", "帕尔梅拉斯", 4.30, 3.30, 1.69, 1.0, (1.88, 3.30, 3.40), "0:4"),
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
    edge_raw = p_model - p_fair
    edge_eff = edge_raw * 0.60
    channel = "不荐"
    if edge_eff >= 0.01:
        channel = "胜平负"
    else:
        wh, wd, wa = hc_probs(lh_sub, la_sub, L)
        hc_map = {"H": wh, "D": wd, "A": wa}
        fair_hc, _ = dewager(*hc_sp)
        e_hc = (hc_map[direction] - fair_hc[direction]) * 0.60
        if e_hc >= 0.03:
            channel = "让球"
    force, flags = p.apply_edge_refine(
        edge_eff, {"H": ph, "D": pd, "A": pa}, fair, market_fav, flags
    )
    # INTEL_FIRST：结果预测锁剧本
    final_dir = direction
    return {
        "date": date,
        "code": code,
        "match": f"{home} vs {away}",
        "league": league,
        "script": final_dir,
        "market_fav": market_fav,
        "actual": actual,
        "score": score,
        "hit": final_dir == actual,
        "mkt_hit": market_fav == actual,
        "Edge_eff%": round(edge_eff * 100, 2),
        "channel": channel,
        "ticket_ok": channel != "不荐",
        "ticket_hit": channel != "不荐" and final_dir == actual,
        "patch": p.format_patch_report(flags).split("\n")[0],
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
    summary = {
        "slate": "竞彩最近30场 2026-07-29～08-02",
        "n": n,
        "dir_hit": hits,
        "dir_acc": round(hits / n, 4),
        "market_hit": mkt,
        "market_acc": round(mkt / n, 4),
        "ticket_n": len(tickets),
        "ticket_hit": th,
        "ticket_acc": round(th / len(tickets), 4) if tickets else None,
        "skill": "football-predict-v17 / V17.4.7 INTEL_FIRST",
        "disclaimer": "澳客指数模拟；情报剧本=胶着带规则；非投资建议",
    }
    out = {"summary": summary, "rows": rows}
    path = ROOT / "scripts" / "backtest_30_ticai.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 72)
    print("V17.4.7 · 最近30场回测", summary["slate"])
    print(
        f"INTEL方向 {hits}/{n}={summary['dir_acc']*100:.1f}%  |  "
        f"市热 {mkt}/{n}={summary['market_acc']*100:.1f}%  |  "
        f"出票 {len(tickets)} 命中 {th}"
    )
    print("=" * 72)
    for r in rows:
        mark = "✓" if r["hit"] else "✗"
        mm = "市✓" if r["mkt_hit"] else "市✗"
        print(
            f"{r['date']}-{r['code']} {mark} {mm} | {r['match']} | "
            f"剧本{r['script']} 市热{r['market_fav']} 实{r['actual']} {r['score']} | "
            f"Edge{r['Edge_eff%']}% {r['channel']}"
        )
    print("\nJSON →", path)
    print("OK", p.VERSION, p.BOUND_TO)


if __name__ == "__main__":
    main()
