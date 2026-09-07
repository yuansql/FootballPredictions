#!/usr/bin/env python3
"""情报质量评分(ICS) · V17.4.24

计算一场比赛的情报完整度分数。
用法：
    python3 scripts/intelligence_checklist.py --fixture "纽卡斯尔 vs 伯恩茅斯" \
        --slots "积分,近5,伤停,H2H" --sources "3" --has-narrative
"""
from __future__ import annotations

import argparse
import sys

# ─── 评分标准 ────────────────────────────────────────────────────────────────

SLOT_WEIGHTS = {
    "积分": 15,
    "近5": 15,
    "伤停": 25,
    "H2H": 15,
    "战意": 15,
    "赛程": 15,
}

SOURCE_BONUS = {
    0: -20,
    1: -10,
    2: 0,
    3: 5,
    4: 10,
    5: 15,
}


def calculate_ics(slots: list[str], source_count: int, has_narrative: bool) -> dict:
    """计算 ICS 分数。"""
    slot_score = sum(SLOT_WEIGHTS.get(s.strip(), 0) for s in slots)
    # 满分100，截断
    slot_score = min(slot_score, 100)

    source_bonus = SOURCE_BONUS.get(min(source_count, 5), 0)

    narrative_bonus = 10 if has_narrative else -15

    total = slot_score + source_bonus + narrative_bonus
    total = max(0, min(100, total))

    return {
        "slot_score": slot_score,
        "source_bonus": source_bonus,
        "narrative_bonus": narrative_bonus,
        "total": total,
    }


def get_action(total: int) -> str:
    if total >= 70:
        return "PROCEED"
    if total >= 50:
        return "CAUTION"
    return "STOP"


def main() -> None:
    parser = argparse.ArgumentParser(description="情报质量评分")
    parser.add_argument("--slots", required=True, help="逗号分隔的取证槽")
    parser.add_argument("--sources", type=int, default=0, help="来源数量")
    parser.add_argument("--has-narrative", action="store_true", help="有情报叙事")
    parser.add_argument("--fixture", default="", help="比赛名")
    args = parser.parse_args()

    slots = [s.strip() for s in args.slots.split(",") if s.strip()]
    result = calculate_ics(slots, args.sources, args.has_narrative)
    action = get_action(result["total"])

    print(f"ICS for {args.fixture or 'fixture'}:")
    print(f"  槽位分: {result['slot_score']}/100")
    print(f"  来源加成: {result['source_bonus']:+.0f}")
    print(f"  叙事加成: {result['narrative_bonus']:+.0f}")
    print(f"  总分 ICS: {result['total']}/100")
    print(f"  建议动作: {action}")

    if action == "STOP":
        sys.exit(1)


if __name__ == "__main__":
    main()
