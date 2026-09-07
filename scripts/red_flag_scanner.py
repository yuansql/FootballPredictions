#!/usr/bin/env python3
"""红旗清单扫描器 · V17.4.24

扫描草稿中的6个红旗信号，输出WARNING。
用法：
    python3 scripts/red_flag_scanner.py --file drafts/2026-09-07/01-竞彩分析.md
"""
from __future__ import annotations

import argparse
import re

RED_FLAGS: list[tuple[str, str]] = [
    ("RF_01", r"几乎不丢球|不丢球|零封.*稳|防线固若金汤"),
    ("RF_02", r"复仇.*必胜|讨债.*稳赢|主场.*必胜"),
    ("RF_03", r"赛程.*完全.*不利|一定.*疲劳"),
    ("RF_04", r"客队.*不可能|主队.*绝对|不可能.*输"),
    ("RF_05", r"正常.*发挥.*就赢|正常打.*就赢"),
    ("RF_06", r"虽然.*但是.*强|虽然.*不过.*必胜"),
]


def scan_red_flags(text: str) -> list[dict]:
    issues: list[dict] = []
    for code, pattern in RED_FLAGS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            line_no = text[:m.start()].count("\n") + 1
            issues.append({
                "code": code,
                "line": line_no,
                "match": m.group(0),
                "message": f"红旗信号: {m.group(0)}",
            })
    return issues


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    args = parser.parse_args()

    with open(args.file, "r", encoding="utf-8") as f:
        text = f.read()

    issues = scan_red_flags(text)
    print(f"红旗扫描: {args.file}")
    print(f"  发现 {len(issues)} 个红旗信号")
    for i in issues:
        print(f"  ⚠️ [{i['code']}] 行{i['line']}: {i['message']}")


if __name__ == "__main__":
    main()
