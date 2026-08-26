#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V17.4.17 准确率钩：RMA / 邻格簇几何 / 收据指纹 shadow。"""
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
    for phrase in ("V17.4.17", "RMA", "邻格簇", "收据指纹"):
        if phrase not in skill:
            print(f"FAIL SKILL missing {phrase}")
            return 1

    print("PASS V17.4.17 accuracy hooks (RMA + neighbor cluster + fingerprint shadow)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
