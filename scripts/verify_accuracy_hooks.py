#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V17.4.20 准确率钩：RMA / 单格 Top3 / counter 防格 / 指纹 TOP2 live。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import rma_route  # noqa: E402
import receipt_fingerprint  # noqa: E402
import score_geometry  # noqa: E402
from receipt_fingerprint import fingerprint_from_fields, load_ledger, shadow_check  # noqa: E402


def main() -> int:
    rma_route._self_check()
    score_geometry._self_check()
    receipt_fingerprint._self_check()

    ledger_path = ROOT / "data/miss_fingerprint_ledger.jsonl"
    ledger = load_ledger(ledger_path)
    fp = fingerprint_from_fields("revenge_home", "script#1", "客胜", 4)
    v = shadow_check(fp, ledger, threshold=2)
    if v.would_demote:
        print(f"OK shadow ledger: {v.reason}")
    else:
        print(f"OK shadow ledger: no demote yet (hits={v.match_count}, need 2 for shadow)")

    skill = (ROOT / "skills/football-predict-v17/SKILL.md").read_text(encoding="utf-8")
    for phrase in (
        "V17.4.20",
        "RMA",
        "单格 Top3",
        "每个比分单独",
        "收据指纹",
        "ht_path",
        "counter_hit",
        "防格",
    ):
        if phrase not in skill:
            print(f"FAIL SKILL missing {phrase}")
            return 1
    if "同等合法" in skill and "禁止" not in skill:
        print("FAIL SKILL still treats 同等合法 as allowed")
        return 1
    if "套餐" not in skill or "禁止" not in skill:
        print("FAIL SKILL must ban 三格套餐/组合")
        return 1

    print("PASS V17.4.20 accuracy hooks (RMA + counter_bind + HT/FT + TOP2 live)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
