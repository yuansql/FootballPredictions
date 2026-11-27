#!/usr/bin/env python3
"""求中奖二串一组票器：自动抓竞彩实际 SP（胜平负 + 进球数），按市场隐含概率组票。

定位：面向「只想中奖、不追 EV」的求中奖玩法，区别于 pick_2chuan1.py（后者吃人工 CSV、
走保守概率、默认合计 SP≥2.00）。本脚本概率来自 devig(市场隐含)，是公共信息共识，
不构成正期望承诺；二串一返奖率 65%，长期结构上为负，仅供娱乐参考。

联网抓取（竞彩官网 webapi）：
  1. 赛程+胜平负/让球 SP：getMatchListV1.qry
  2. 每场进球数 8 档 SP：getFixedBonusV1.qry?matchId=<id>

形态：
  --form spf-spf    胜平负 × 胜平负（跨场）
  --form spf-ttg    胜平负 × 进球数（另一场，进球数按相邻双档复式）
  --form both       两种形态都出（默认）

过滤：
  --min-sp   最低合计 SP（默认 2.00；低于此「中了也可能亏」，建议保留门槛）
  --top      每种形态展示前 N 组（默认 5）

用法：
  python3 scripts/market_parlay.py                    # 全部形态，SP>=2.00
  python3 scripts/market_parlay.py --form spf-ttg     # 只要胜平负+进球数双选
  python3 scripts/market_parlay.py --min-sp 1.5 --top 8
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from itertools import combinations

API = "https://webapi.sporttery.cn/gateway/uniform/football"
HEADERS = {
    "Referer": "https://www.sporttery.cn/",
    "User-Agent": "Mozilla/5.0 (compatible; sporttery-parlay)",
}
TTG_LABEL = {0: "0球", 1: "1球", 2: "2球", 3: "3球",
             4: "4球", 5: "5球", 6: "6球", 7: "7+球"}


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def devig(pairs):
    """pairs=[(label, sp)] → {label: 归一化概率}。去掉水位，得到市场隐含概率。"""
    inv = {lab: 1.0 / sp for lab, sp in pairs if sp and sp > 1}
    if len(inv) < 2:
        raise ValueError(f"有效赔率不足（需≥2个 sp>1）：{pairs}")
    total = sum(inv.values())
    if total <= 0:
        raise ValueError(f"概率归一化失败（总和非正）：{pairs}")
    return {lab: p / total for lab, p in inv.items()}


def fetch_matches() -> dict:
    """抓赛程 + 胜平负 SP，返回 {match_id: match dict}。"""
    url = f"{API}/getMatchListV1.qry?clientCode=3001"
    data = _get_json(url)
    matches = {}
    for day in data["value"]["matchInfoList"]:
        for m in day.get("subMatchList", []) or []:
            odds = {o["poolCode"]: o for o in (m.get("oddsList") or [])}
            had = odds.get("HAD")  # 胜平负
            try:
                h, d, a = float(had["h"]), float(had["d"]), float(had["a"])
            except (TypeError, ValueError, KeyError):
                continue
            matches[m["matchId"]] = {
                "id": m["matchId"],
                "num": m["matchNumStr"],
                "league": m["leagueAbbName"],
                "home": m["homeTeamAbbName"],
                "away": m["awayTeamAbbName"],
                "spf_sp": {"主": h, "平": d, "客": a},
                "ttg_sp": {},
            }
    return matches


def fetch_ttg(matches: dict) -> None:
    """逐场抓进球数 8 档 SP，写回 matches[*]['ttg_sp']。"""
    for mid, m in matches.items():
        try:
            data = _get_json(f"{API}/getFixedBonusV1.qry?matchId={mid}")
            ttg = data["value"]["oddsHistory"]["ttgList"][0]
            sp = {}
            for i in range(8):
                v = ttg.get(f"s{i}")
                if v and float(v) > 1:
                    sp[i] = float(v)
            if len(sp) >= 4:
                m["ttg_sp"] = sp
            else:
                print(f"  [warn] {m['num']} 进球数档位不足（{len(sp)}/8），跳过",
                      file=sys.stderr)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            print(f"  [warn] {m['num']} 进球数解析异常：{exc}", file=sys.stderr)
        except Exception as exc:
            print(f"  [warn] {m['num']} 进球数请求失败：{exc}", file=sys.stderr)
        time.sleep(0.15)  # 礼貌限速


def build_candidates(matches: dict) -> list:
    """展开成扁平候选列表。进球数存为「相邻双档」选项（复式，覆盖两档概率）。"""
    cands = []
    for m in matches.values():
        # 胜平负
        p = devig(list(m["spf_sp"].items()))
        for lab, sp in m["spf_sp"].items():
            cands.append({
                "match_id": m["id"], "num": m["num"], "match": f"{m['home']}vs{m['away']}",
                "play": "胜平负", "opt": lab, "sp": sp, "p": p[lab],
                "multi": 1,  # 单式，1 注
            })
        # 进球数：相邻双档打包（g 与 g+1），取覆盖概率最高的相邻对
        if m["ttg_sp"]:
            tp = devig(list(m["ttg_sp"].items()))
            best = None
            for g in range(7):
                if g in tp and (g + 1) in tp:
                    cov = tp[g] + tp[g + 1]
                    if best is None or cov > best["p"]:
                        best = {
                            "match_id": m["id"], "num": m["num"],
                            "match": f"{m['home']}vs{m['away']}",
                            "play": "进球数", "opt": f"{TTG_LABEL[g]}+{TTG_LABEL[g+1]}",
                            "sp": (m["ttg_sp"][g] + m["ttg_sp"][g + 1]) / 2,  # 展示用均赔
                            "p": cov, "multi": 2,  # 复式 2 注
                        }
            if best:
                cands.append(best)
    return cands


def best_parlays(cands: list, form: str, min_sp: float, top: int) -> None:
    spf = [c for c in cands if c["play"] == "胜平负"]
    ttg = [c for c in cands if c["play"] == "进球数"]

    def parlay(pool_a, pool_b, title):
        rows = []
        for a in pool_a:
            for b in pool_b:
                if a["match_id"] == b["match_id"]:
                    continue  # 必须跨场
                total_sp = a["sp"] * b["sp"]
                if total_sp < min_sp:
                    continue
                rows.append({
                    "a": a, "b": b, "sp": total_sp, "p": a["p"] * b["p"],
                    "notes": a["multi"] * b["multi"],  # 总注数（进球双选翻倍）
                })
        rows.sort(key=lambda r: -r["p"])
        print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")
        if not rows:
            print(f"无可行组合（合计SP≥{min_sp:.2f}）。本日该形态=空仓。")
            return
        for i, r in enumerate(rows[:top], 1):
            a, b = r["a"], r["b"]

            def tag(c):
                return "(双选)" if c["multi"] == 2 else ""

            payout = r["sp"] * 2 * 0.65  # 单注理论返还 = 2元 × 合计SP × 返奖率65%
            cost = r["notes"] * 2  # 复式时 notes=2，本金翻倍
            print(f"#{i} {a['num']}·{a['play']}{a['opt']}{tag(a)}({a['sp']:.2f}) × "
                  f"{b['num']}·{b['play']}{b['opt']}{tag(b)}({b['sp']:.2f})")
            print(f"   {a['match']}  +  {b['match']}")
            print(f"   合计SP={r['sp']:.2f}｜联合中奖={r['p'] * 100:.1f}%｜"
                  f"本金={cost}元｜命中返还≈{payout:.2f}元｜净≈{payout - cost:+.2f}元")
        best = rows[0]
        print(f"推荐=第1组（规则：合计SP≥{min_sp:.2f} + 联合中奖最高；非正期望承诺）")

    if form in ("spf-spf", "both"):
        parlay(spf, spf, "形态1：胜平负 × 胜平负（跨场）")
    if form in ("spf-ttg", "both"):
        parlay(spf, ttg, "形态2：胜平负 × 进球数双选（跨场，进球数复式2注）")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--form", choices=["spf-spf", "spf-ttg", "both"], default="both",
                   help="票面形态，默认 both")
    p.add_argument("--min-sp", type=float, default=2.0,
                   help="最低合计 SP（默认 2.00，低于此中了易亏）")
    p.add_argument("--top", type=int, default=5, help="每形态展示前 N 组")
    p.add_argument("--no-ttg", action="store_true", help="跳过进球数抓取（更快）")
    args = p.parse_args(argv)

    print("抓取竞彩赛程与胜平负 SP ...")
    matches = fetch_matches()
    if not matches:
        print("未抓到任何在售场次（可能非销售时段或接口变更）")
        return 1
    print(f"在售场次={len(matches)}")

    if args.form in ("spf-ttg", "both") and not args.no_ttg:
        print("逐场抓取进球数 SP ...")
        fetch_ttg(matches)

    cands = build_candidates(matches)
    spf_n = sum(1 for c in cands if c["play"] == "胜平负")
    ttg_n = sum(1 for c in cands if c["play"] == "进球数")
    print(f"候选选项：胜平负 {spf_n} 个，进球数双选 {ttg_n} 个")

    best_parlays(cands, args.form, args.min_sp, args.top)

    print("\n" + "-" * 72)
    print("提示：二串一返奖率 65%，长期结构为负；概率=市场隐含（devig），非预测保证。")
    print("      出票前请临场复核 SP，SP 会随投注量变动。仅供娱乐，理性购彩。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
