#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量复盘统计：方向率 / 比分挂率 / RMA 分仓（V17.4.16）。"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rma_route import (
    outcome_1x2,
    parse_score,
    public_allowed_set,
    route_rma_public,
    score_in_basket,
)

ROW_RE = re.compile(
    r"^\|\s*(?:TOP\d+|边|\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*\*\*(.+?)\*\*",
    re.M,
)
SCORES_IN_CELL = re.compile(r"(\d+-\d+)")


def _actual_1x2(score_cell: str) -> str | None:
    m = re.search(r"\*\*(\d+-\d+)\*\*", score_cell)
    if not m:
        m = SCORES_IN_CELL.search(score_cell)
    if not m:
        return None
    parsed = parse_score(m.group(1))
    if not parsed:
        return None
    return outcome_1x2(*parsed)


def _actual_score(score_cell: str) -> str | None:
    m = re.search(r"\*\*(\d+-\d+)\*\*", score_cell)
    if m:
        return m.group(1)
    hits = SCORES_IN_CELL.findall(score_cell)
    return hits[0] if hits else None


def _basket_from_cell(cell: str) -> list[str]:
    return SCORES_IN_CELL.findall(cell.replace("·", "/").replace(" ", ""))


def parse_review(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    rows: list[dict] = []
    for m in ROW_RE.finditer(text):
        match, direction, scores, result = m.group(1), m.group(2), m.group(3), m.group(4)
        actual = _actual_score(result)
        if not actual:
            continue
        parsed = parse_score(actual)
        if not parsed:
            continue
        a1x2 = outcome_1x2(*parsed)
        basket = _basket_from_cell(scores)
        claim = public_allowed_set(direction, basket)
        counts = bool(claim)
        rma = route_rma_public(direction, a1x2, basket, actual)
        rows.append(
            {
                "match": match.strip(),
                "direction": direction.strip(),
                "basket": basket,
                "actual_score": actual,
                "actual_1x2": a1x2,
                "counts_public": counts,
                "direction_ok": (a1x2 in claim) if counts else False,
                "score_ok": score_in_basket(actual, basket) if counts else False,
                "rma": rma.value,
            }
        )
    return rows


def summarize(all_rows: list[dict]) -> dict:
    countable = [r for r in all_rows if r.get("counts_public", True)]
    n = len(countable)
    skipped = len(all_rows) - n
    if n == 0:
        return {"n": 0, "skipped": skipped}
    dir_ok = sum(1 for r in countable if r["direction_ok"])
    score_ok = sum(1 for r in countable if r["score_ok"])
    rma_counts: dict[str, int] = {}
    for r in all_rows:
        rma_counts[r["rma"]] = rma_counts.get(r["rma"], 0) + 1
    return {
        "n": n,
        "skipped": skipped,
        "direction_rate": dir_ok / n,
        "score_rate": score_ok / n,
        "score_rate_given_dir_ok": sum(1 for r in countable if r["direction_ok"] and r["score_ok"])
        / max(1, dir_ok),
        "rma": rma_counts,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Replay RMA stats from 03-复盘.md files")
    ap.add_argument(
        "root",
        nargs="?",
        default="/Users/wumm/学习/@@Agent/toutiao/drafts",
        help="drafts root",
    )
    args = ap.parse_args()
    root = Path(args.root)
    all_rows: list[dict] = []
    files = sorted(root.glob("*/03-复盘.md"))
    for f in files:
        rows = parse_review(f)
        if rows:
            print(f"## {f.parent.name} ({len(rows)} matches)")
            for r in rows:
                mark = "✓" if r["score_ok"] else "·"
                dmark = "D—" if not r.get("counts_public", True) else (
                    "D✓" if r["direction_ok"] else "D✗"
                )
                print(
                    f"  {dmark} {mark} [{r['rma']}] {r['match'][:30]} "
                    f"{r['actual_score']} | basket={r['basket']}"
                )
            all_rows.extend(rows)

    s = summarize(all_rows)
    print("\n=== TOTAL ===")
    if not all_rows:
        print("no parsed rows (need 对照表 with **score** in 赛果列)")
        return 1
    if s["n"] == 0:
        print(f"matches=0 skipped={s.get('skipped', 0)} (all vacant/skip)")
        print(f"RMA={s.get('rma', {})}")
        return 0
    print(f"matches={s['n']} skipped={s.get('skipped', 0)}")
    print(f"direction_hit={s['direction_rate']:.1%}")
    print(f"score_hit={s['score_rate']:.1%}")
    print(f"score_hit|direction_ok={s['score_rate_given_dir_ok']:.1%}")
    print(f"RMA={s['rma']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
