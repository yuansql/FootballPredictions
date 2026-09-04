#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一 prediction_log.jsonl 追加/验证器（Phase A）。

所有预测、复盘、回测脚本最终都应通过本工具写入 data/prediction_log.jsonl，
避免各自维护 ad-hoc JSON/JSONL 文件。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    import jsonschema
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "jsonschema is required. Run: pip install -r scripts/requirements.txt"
    ) from exc

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "prediction_log.json"
DEFAULT_LOG_PATH = ROOT / "data" / "prediction_log.jsonl"
SCHEMA_VERSION = "1.0.0"


def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate(row: dict[str, Any], schema: dict[str, Any] | None = None) -> None:
    """Validate a log row against the canonical schema. Raises on failure."""
    if schema is None:
        schema = load_schema()
    jsonschema.validate(row, schema)


def append(
    row: dict[str, Any],
    log_path: Path = DEFAULT_LOG_PATH,
    schema: dict[str, Any] | None = None,
) -> Path:
    """Validate and append a row to the canonical log."""
    row.setdefault("schema_version", SCHEMA_VERSION)
    validate(row, schema)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return log_path


def append_many(
    rows: list[dict[str, Any]],
    log_path: Path = DEFAULT_LOG_PATH,
    schema: dict[str, Any] | None = None,
) -> Path:
    for row in rows:
        append(row, log_path=log_path, schema=schema)
    return log_path


def read_log(log_path: Path = DEFAULT_LOG_PATH) -> list[dict[str, Any]]:
    if not log_path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _self_check() -> None:
    schema = load_schema()
    sample = {
        "run_id": "20260803-test",
        "date": "2026-08-03",
        "match": "塞伊奈 vs 赫尔辛基",
        "league": "芬超",
        "skill_version": "V17.4.22.4",
        "intel_slots": ["伤停", "H2H"],
        "pre_match": {
            "research_direction": "客胜",
            "public_claim": "客胜",
            "scores_basket": ["1-2", "0-1", "1-1"],
            "edge_eff_pct": 1.75,
            "channel": "胜平负",
        },
        "post_match": {
            "actual_score": "1-2",
            "actual_1x2": "客胜",
            "rma_route": "closed",
        },
    }
    validate(sample, schema)
    print("OK log_append schema validation")


def main() -> int:
    ap = argparse.ArgumentParser(description="Append/validate prediction log rows")
    ap.add_argument(
        "--log",
        type=Path,
        default=DEFAULT_LOG_PATH,
        help=f"Path to prediction log (default: {DEFAULT_LOG_PATH})",
    )
    ap.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate stdin rows without appending",
    )
    args = ap.parse_args()

    schema = load_schema()
    rows = []
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        validate(row, schema)
        rows.append(row)

    if args.validate_only:
        print(f"Validated {len(rows)} row(s)")
        return 0

    for row in rows:
        append(row, log_path=args.log, schema=schema)
    print(f"Appended {len(rows)} row(s) to {args.log}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
