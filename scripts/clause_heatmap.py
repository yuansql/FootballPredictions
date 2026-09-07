#!/usr/bin/env python3
"""Clause 准确率热力图 · V17.4.24 P5

从复盘文件(03-复盘.md)中提取每个clause的使用频率和准确率，
生成热力图数据，识别真有效 vs 假闸。

用法：
    python3 scripts/clause_heatmap.py --reviews-dir docs/backtest/

输出：
    clause,uses,hits,misses,accuracy,action
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


CLAUSE_PATTERNS: dict[str, str] = {
    "revenge_home": r"revenge_home|主场讨债|复仇",
    "weld_draw": r"weld_draw|焊平|势均力敌",
    "manage_tie": r"manage_tie|管理比赛|晋级管理",
    "derby_caution": r"derby_caution|德比|谨慎",
    "continuation_guest": r"continuation_guest|同址客队|刚赢再战",
    "draw_priority": r"draw_priority|低结构|平优先",
    "deep_away_trap": r"deep_away_trap|深盘陷阱|豪门客场",
    "starfactor": r"StarFactor|客队三强|后防伤",
    "kryptonite": r"Kryptonite|交锋.*胜",
    "jinx": r"Jinx|主场.*平",
    "zombie": r"Zombie|垫底|受让",
    "edge_refine": r"Edge_Refine|冷门扫描",
}


def parse_review_file(path: Path) -> list[dict[str, Any]]:
    """解析单个复盘文件，提取每场比赛的clause和结果。"""
    text = path.read_text(encoding="utf-8")
    matches: list[dict[str, Any]] = []

    # 简单解析：找 "clause_id=" 和 "RMA=" 行
    for block in text.split("##"):
        clauses: list[str] = []
        rma = None

        for line in block.splitlines():
            # 提取 clause_id
            m = re.search(r"clause_id[=:](\S+)", line)
            if m:
                cid = m.group(1).strip()
                # 简化：取clause名
                for name in CLAUSE_PATTERNS:
                    if name.lower() in cid.lower():
                        clauses.append(name)
                        break

            # 提取 RMA
            m = re.search(r"RMA[=:](\S+)", line)
            if m:
                rma = m.group(1).strip()

            # 提取方向结果
            m = re.search(r"方向[命中miss错]+|direction_(hit|miss)", line)
            if m:
                direction_result = "hit" if "hit" in line or "命中" in line else "miss"

        if clauses and rma:
            for c in clauses:
                matches.append({
                    "clause": c,
                    "rma": rma,
                    "direction_hit": direction_result if "direction" in locals() else None,
                })

    return matches


def build_heatmap(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    stats: dict[str, dict[str, Any]] = {}
    for r in records:
        c = r["clause"]
        if c not in stats:
            stats[c] = {"uses": 0, "hits": 0, "misses": 0}
        stats[c]["uses"] += 1
        if r.get("direction_hit") == "hit":
            stats[c]["hits"] += 1
        elif r.get("direction_hit") == "miss":
            stats[c]["misses"] += 1

    # 计算准确率和建议
    for c, s in stats.items():
        total = s["hits"] + s["misses"]
        s["accuracy"] = round(s["hits"] / total * 100, 1) if total > 0 else 0
        if s["uses"] >= 5:
            if s["accuracy"] >= 70:
                s["action"] = "KEEP"
            elif s["accuracy"] >= 50:
                s["action"] = "REVIEW"
            else:
                s["action"] = "DOWNGRADE"
        else:
            s["action"] = "NEED_MORE_DATA"

    return stats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviews-dir", required=True, help="复盘文件目录")
    args = parser.parse_args()

    reviews_dir = Path(args.reviews_dir)
    all_records: list[dict[str, Any]] = []

    for md in sorted(reviews_dir.glob("*.md")):
        records = parse_review_file(md)
        all_records.extend(records)

    if not all_records:
        print("没有找到复盘数据。请先写 03-复盘.md 文件。")
        return

    heatmap = build_heatmap(all_records)

    print("Clause 准确率热力图")
    print("=" * 60)
    print(f"{'Clause':<20} {'Uses':>5} {'Hits':>5} {'Miss':>5} {'Acc%':>6} {'Action':>12}")
    print("-" * 60)
    for clause, data in sorted(heatmap.items(), key=lambda x: -x[1]["accuracy"]):
        print(f"{clause:<20} {data['uses']:>5} {data['hits']:>5} {data['misses']:>5} "
              f"{data['accuracy']:>5.1f}% {data['action']:>12}")

    # 输出建议
    print("\n建议:")
    for clause, data in heatmap.items():
        if data["action"] == "DOWNGRADE":
            print(f"  ⚠️ {clause}: 准确率{data['accuracy']}% < 50%，建议降级或删除")
        elif data["action"] == "REVIEW":
            print(f"  🟡 {clause}: 准确率{data['accuracy']}% 50-70%，建议复盘原因")


if __name__ == "__main__":
    main()
