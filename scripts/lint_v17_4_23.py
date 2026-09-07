#!/usr/bin/env python3
"""V17.4.23 补丁 linter：低结构闸 + 焊叙事检测 + 深盘陷阱（追加检查）。

用法：
    python3 scripts/lint_v17_4_23.py 2026-09-04  # 检查某日草稿

此脚本与外部原有 lint_draft.py（V17.4.22.4）互补使用：
- lint_draft.py 负责 TOP2 闸、RMA 收据、HT/FT、方向必给等基础铁律
- lint_v17_4_23.py 负责 V17.4.23 新增三补丁的专项检测
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

# ─── 辅助解析 ────────────────────────────────────────────────────────────────

def _parse_sections(text: str) -> list[dict[str, Any]]:
    """从草稿文本提取比赛块（简易版）。"""
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    buf: list[str] = []

    for line in text.splitlines():
        if re.search(r"^\s*[-=•]+\s*[【\[]?\d+[.、]\s*", line):
            if current and buf:
                current["body"] = "\n".join(buf)
                sections.append(current)
            current = {"header": line.strip(), "body": ""}
            buf = []
        elif current is not None:
            buf.append(line)

    if current and buf:
        current["body"] = "\n".join(buf)
        sections.append(current)

    return sections


def _extract_direction(body: str) -> str:
    m = re.search(r"方向[:：]\s*([^\n]+)", body)
    return (m.group(1).strip() if m else "")


def _extract_lean(body: str) -> str:
    m = re.search(r"单子倾向[:：]\s*([^\n]+)", body)
    return (m.group(1).strip() if m else "")


def _extract_sp(body: str) -> tuple[float, float, float] | None:
    """提取 SP_H, SP_D, SP_A。"""
    m = re.search(r"SP[:：]\s*(\d+\.\d+)\s*/\s*(\d+\.\d+)\s*/\s*(\d+\.\d+)", body)
    if m:
        return float(m.group(1)), float(m.group(2)), float(m.group(3))
    return None


# ─── P0: 低结构平优先闸 ─────────────────────────────────────────────────────

def lint_low_structure_weld(sections: list[dict], day: str | None = None) -> list[dict]:
    """检测低结构场是否焊死主胜/客胜。"""
    issues: list[dict] = []
    for sec in sections:
        body = sec.get("body", "")
        sp = _extract_sp(body)
        if not sp:
            continue
        sp_h, sp_d, sp_a = sp

        draw_priority = False
        if sp_h > 2.0 and sp_a > 2.0 and abs(sp_h - sp_a) < 1.5:
            draw_priority = True
        if sp_d < 3.0:
            draw_priority = True
        if max(sp_h, sp_a) / min(sp_h, sp_a) < 1.8:
            draw_priority = True

        if not draw_priority:
            continue

        lean = _extract_lean(body)
        if "主胜" in lean or "客胜" in lean or lean == "平":
            issues.append({
                "section": sec.get("header", "")[:40],
                "rule": "P0_draw_priority_weld",
                "message": f"低结构场(SP {sp_h}/{sp_d}/{sp_a})倾向焊死「{lean}」→ 应写「不定」",
                "severity": "ERROR",
            })
    return issues


# ─── P0: 焊叙事检测 ──────────────────────────────────────────────────────────

def lint_02_atom_text(sections: list[dict], day: str | None = None) -> list[dict]:
    """检测硬焊「防平」等原子化短语。"""
    issues: list[dict] = []
    bad_patterns = ["防平", "主胜防平", "客胜防平", "必平", "铁平局"]
    for sec in sections:
        body = sec.get("body", "")
        for pat in bad_patterns:
            if pat in body:
                issues.append({
                    "section": sec.get("header", "")[:40],
                    "rule": "P0_atom_weld",
                    "message": f"检测到硬焊短语「{pat}」→ 用方向+防格代替",
                    "severity": "WARN",
                })
                break
    return issues


# ─── P0: 方向必给 ────────────────────────────────────────────────────────────

def lint_02_must_direction(sections: list[dict], day: str | None = None) -> list[dict]:
    """每场比赛必须给出方向（主不败/客不败/锁平），禁止空槽。"""
    issues: list[dict] = []
    for sec in sections:
        body = sec.get("body", "")
        direction = _extract_direction(body)
        if not direction or direction in ("胶着", "并列", "不定"):
            issues.append({
                "section": sec.get("header", "")[:40],
                "rule": "P0_missing_direction",
                "message": f"方向缺失或无效「{direction}」→ 必须给主不败/客不败/锁平",
                "severity": "ERROR",
            })
    return issues


# ─── P0: 倾向合法性 ──────────────────────────────────────────────────────────

def lint_lean_pack(sections: list[dict], day: str | None = None) -> list[dict]:
    """检测倾向是否属于允许集。"""
    allowed = {"主胜", "客胜", "平", "不定", "偏主", "偏客", "偏平"}
    issues: list[dict] = []
    for sec in sections:
        body = sec.get("body", "")
        lean = _extract_lean(body)
        if lean and lean not in allowed and not any(a in lean for a in allowed):
            issues.append({
                "section": sec.get("header", "")[:40],
                "rule": "P0_invalid_lean",
                "message": f"倾向「{lean}」不在允许集 → 用主胜/客胜/平/不定/偏主/偏客/偏平",
                "severity": "WARN",
            })
    return issues


# ─── P2: 深盘陷阱 ────────────────────────────────────────────────────────────

def lint_deep_away_trap(sections: list[dict], day: str | None = None) -> list[dict]:
    """检测豪门客场深盘未做确认书。"""
    BIG_CLUBS = {
        "曼城", "利物浦", "阿森纳", "曼联", "切尔西",
        "皇马", "巴塞罗那", "马竞",
        "拜仁", "多特蒙德", "勒沃库森",
        "尤文图斯", "国际米兰", "AC米兰",
        "巴黎圣日耳曼",
    }
    issues: list[dict] = []
    for sec in sections:
        body = sec.get("body", "")
        sp = _extract_sp(body)
        if not sp:
            continue
        _, _, sp_a = sp
        if sp_a > 1.50:
            continue

        # 判断客队是否豪门（从头文中提取客队名，简化处理）
        header = sec.get("header", "")
        is_big = any(club in header for club in BIG_CLUBS)
        if not is_big:
            continue

        if "确认书" not in body and "战意衰减" not in body and "客场疲劳" not in body:
            issues.append({
                "section": header[:40],
                "rule": "P2_deep_away_trap",
                "message": f"豪门客场深盘(SP_A={sp_a})未写确认书 → 须补战意衰减+客场疲劳评估",
                "severity": "WARN",
            })
    return issues


# ─── 主入口 ──────────────────────────────────────────────────────────────────

def lint_day_dir(day_dir: Path) -> list[dict]:
    all_issues: list[dict] = []
    for md in sorted(day_dir.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        sections = _parse_sections(text)
        all_issues.extend(lint_low_structure_weld(sections))
        all_issues.extend(lint_02_atom_text(sections))
        all_issues.extend(lint_02_must_direction(sections))
        all_issues.extend(lint_lean_pack(sections))
        all_issues.extend(lint_deep_away_trap(sections))
    return all_issues


def main() -> None:
    if len(sys.argv) < 2:
        print("用法: python3 lint_v17_4_23.py <day_dir_or_date>")
        sys.exit(1)

    arg = sys.argv[1]
    day_path = Path(arg)
    if not day_path.exists():
        # 尝试 drafts/YYYY-MM-DD 格式
        day_path = Path("drafts") / arg

    if not day_path.exists():
        print(f"找不到目录: {day_path}")
        sys.exit(1)

    issues = lint_day_dir(day_path)
    errors = [i for i in issues if i.get("severity") == "ERROR"]
    warns = [i for i in issues if i.get("severity") == "WARN"]

    print(f"V17.4.23 补丁检查: {day_path}")
    print(f"  ERROR: {len(errors)}  WARN: {len(warns)}")
    for i in issues:
        flag = "❌" if i.get("severity") == "ERROR" else "⚠️"
        print(f"  {flag} [{i['rule']}] {i['message']} (in {i['section']})")

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
