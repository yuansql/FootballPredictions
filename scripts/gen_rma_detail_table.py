#!/usr/bin/env python3
"""gen_rma_detail_table.py — rma-*.json → 04-详细对账表.md（V17.4.38 复盘交付）

Usage:
  python3 scripts/gen_rma_detail_table.py path/to/rma-sun-YYYY-MM-DD.json \\
    -o path/to/drafts/YYYY-MM-DD/04-详细对账表.md

JSON shape (minimal):
  { "stats": { "ex":[a,n], "dir":[b,n], "lean":[e,k], "score":[d,n] },
    "rows": [ { "code","teams","ex","dir","lean","scores","ht","ft","actual",
                "ex_hit","dir_hit","lean_hit","score_hit","rma" }, ... ] }
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def mark(v):
    if v is None:
        return "—"
    return "✓" if v else "✗"


def rma_zh(r: str) -> str:
    return {
        "closed": "中",
        "score_rework": "比分",
        "direction_rework": "方向",
        "skip": "skip",
    }.get(r, r)


def pct(pair) -> str:
    hit, n = pair
    if not n:
        return "—（0）"
    return f"**{100.0 * hit / n:.1f}%**（{hit}/{n}）"


def main() -> int:
    ap = argparse.ArgumentParser(description="RMA JSON → 04 markdown detail table")
    ap.add_argument("json_path", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--title", default="", help="optional H1 override")
    args = ap.parse_args()

    data = json.loads(args.json_path.read_text(encoding="utf-8"))
    rows = data["rows"]
    stats = data.get("stats") or {}

    title = args.title or f"全表详细对账 · {args.json_path.stem}"
    lines = [
        f"# {title}\n",
        f"\n源：`{args.json_path.name}`｜生成：gen_rma_detail_table.py\n",
        "\n## 四率摘要\n\n",
        "| 排除 | 推方向 | 单子倾向 | 比分 |\n",
        "|------|--------|----------|------|\n",
    ]
    if stats:
        lines.append(
            f"| {pct(stats.get('ex', [0, 0]))} | {pct(stats.get('dir', [0, 0]))} | "
            f"{pct(stats.get('lean', [0, 0]))} | {pct(stats.get('score', [0, 0]))} |\n"
        )
    else:
        lines.append("| （无 stats） | | | |\n")

    lines.append("\n## 全场明细\n\n")
    lines.append(
        "| 编号 | 对阵 | 排除 | 推方向 | 单子倾向 | 推比分（主/次/防） | 半场 | 全场 | "
        "实际1X2 | 排除 | 方向 | 倾向 | 比分 | RMA |\n"
    )
    lines.append(
        "|------|------|------|--------|----------|-------------------|------|------|"
        "---------|------|------|------|------|-----|\n"
    )
    for r in rows:
        lines.append(
            f"| {r['code']} | {r['teams']} | {r['ex']} | {r['dir']} | {r['lean']} | "
            f"{r.get('scores', '')} | {r.get('ht', '')} | **{r.get('ft', '')}** | "
            f"{r.get('actual', '')} | {mark(r.get('ex_hit'))} | {mark(r.get('dir_hit'))} | "
            f"{mark(r.get('lean_hit'))} | {mark(r.get('score_hit'))} | {rma_zh(r.get('rma', ''))} |\n"
        )
    lines.append(
        "\n图例：✓命中 · ✗未中 · —不定不计倾向分母｜"
        "RMA：中=闭合 · 比分=方向对分未挂 · 方向=方向 miss\n"
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(lines), encoding="utf-8")
    print(f"wrote {args.output} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
