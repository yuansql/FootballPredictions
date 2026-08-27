#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""反剧本收据指纹 · shadow 闸（V17.4.16 · ADHD）。"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ReceiptFingerprint:
    weld_tag: str
    clause_id: str
    counter_direction: str
    intel_slot_shape: str  # e.g. "4/6"

    def key(self) -> tuple[str, str, str, str]:
        return (self.weld_tag, self.clause_id, self.counter_direction, self.intel_slot_shape)


@dataclass
class ShadowVerdict:
    would_demote: bool
    match_count: int
    reason: str


def fingerprint_from_fields(
    weld_tag: str,
    clause_id: str,
    counter_direction: str,
    intel_slots_filled: int,
    intel_slots_total: int = 6,
) -> ReceiptFingerprint:
    return ReceiptFingerprint(
        weld_tag=weld_tag or "none",
        clause_id=clause_id or "none",
        counter_direction=counter_direction or "none",
        intel_slot_shape=f"{intel_slots_filled}/{intel_slots_total}",
    )


def load_ledger(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def shadow_check(
    fp: ReceiptFingerprint,
    ledger: Iterable[dict],
    *,
    window: int = 10,
    threshold: int = 2,
) -> ShadowVerdict:
    """Shadow：只警告，不硬拦。近 window 条 direction miss 中同指纹 ≥ threshold → would_demote。"""
    recent = list(ledger)[-window:]
    key = fp.key()
    hits = 0
    for row in recent:
        if row.get("outcome") != "direction_miss":
            continue
        other = (
            row.get("weld_tag", "none"),
            row.get("clause_id", "none"),
            row.get("counter_direction", "none"),
            row.get("intel_slot_shape", "none"),
        )
        if other == key:
            hits += 1
    if hits >= threshold:
        return ShadowVerdict(
            would_demote=True,
            match_count=hits,
            reason=f"指纹 {key} 近 {window} 条方向 miss 中命中 {hits} 次（shadow，未硬拦）",
        )
    return ShadowVerdict(would_demote=False, match_count=hits, reason="ok")


def counter_hit_shadow_check(
    fp: ReceiptFingerprint,
    ledger: Iterable[dict],
    *,
    window: int = 10,
    threshold: int = 1,
) -> ShadowVerdict:
    """TOP2 live：近 window 条 direction_miss 中同指纹且 counter_hit ≥ threshold → 硬拦 TOP2。"""
    recent = list(ledger)[-window:]
    key = fp.key()
    hits = 0
    for row in recent:
        if row.get("outcome") != "direction_miss":
            continue
        sub = str(row.get("subtag", "") or "")
        note = str(row.get("note", "") or "")
        if "counter_hit" not in sub and "counter_hit" not in note:
            continue
        other = (
            row.get("weld_tag", "none"),
            row.get("clause_id", "none"),
            row.get("counter_direction", "none"),
            row.get("intel_slot_shape", "none"),
        )
        if other == key:
            hits += 1
    if hits >= threshold:
        return ShadowVerdict(
            would_demote=True,
            match_count=hits,
            reason=f"指纹 {key} 已 counter_hit {hits} 次（TOP2 live 拦）",
        )
    return ShadowVerdict(would_demote=False, match_count=hits, reason="ok")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _self_check() -> None:
    fp = fingerprint_from_fields("revenge_home", "script#1", "客胜", 4)
    ledger = [
        {
            "date": "2026-08-25",
            "match": "森林 vs 利兹",
            "outcome": "direction_miss",
            **asdict(fp),
        },
        {
            "date": "2026-08-20",
            "match": "示例",
            "outcome": "direction_miss",
            **asdict(fp),
        },
    ]
    v = shadow_check(fp, ledger, threshold=2)
    assert v.would_demote
    v2 = shadow_check(fp, ledger[:1], threshold=2)
    assert not v2.would_demote
    ledger[0]["subtag"] = "counter_hit"
    v3 = counter_hit_shadow_check(fp, ledger[:1], threshold=1)
    assert v3.would_demote
    v4 = counter_hit_shadow_check(fp, ledger[1:], threshold=1)
    assert not v4.would_demote
    print("OK receipt_fingerprint self-check")


if __name__ == "__main__":
    _self_check()
