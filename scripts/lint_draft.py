#!/usr/bin/env python3
"""
lint_draft.py — V17.4.23 日闸 lint 工具

功能：
1. lint_low_structure_weld — 扫描 draw_priority 场是否焊死倾向
2. lint_02_atom_text — 检查 02 对外句面是否含「防平」硬焊措辞
3. lint_02_must_direction — 验证每场方向原子必给（4.22.3）
4. lint_lean_pack — 验证倾向 ∈ 允许集（4.22.4）

用法：
    python3 lint_draft.py <草稿文件.md> [--day YYYY-MM-DD]
    python3 lint_draft.py /path/to/01-竞彩分析.md --day 2026-09-07

日闸常量：
    STRUCTURE_GATE_DAY = "2026-09-07"
    DIR_MUST_DAY = "2026-09-02"
    LEAN_DAY = "2026-09-04"
"""

import sys
import re
import argparse
from datetime import datetime

# === 日闸常量 ===
STRUCTURE_GATE_DAY = "2026-09-07"
DIR_MUST_DAY = "2026-09-02"
LEAN_DAY = "2026-09-04"

# === 导入 structure_gate ===
import importlib.util
import os

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("structure_gate", os.path.join(_SCRIPT_DIR, "structure_gate.py"))
structure_gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(structure_gate)

compute_structure_tag = structure_gate.compute_structure_tag
get_enforced_direction = structure_gate.get_enforced_direction
parse_sp_line = structure_gate.parse_sp_line


def parse_sections(filepath: str) -> list[dict]:
    """解析 markdown 草稿文件，返回比赛段列表。"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    sections = []
    parts = re.split(r'\n## ', content)
    for part in parts:
        lines = part.strip().split('\n')
        if not lines:
            continue
        header = lines[0].strip().lstrip('#').strip()
        # 跳过非比赛段（复盘/附录/模板/TOP列表等）
        skip_keywords = ['复盘', '附录', '总体', '模板', '今晚研究', '钉槽', '目录']
        if any(k in header for k in skip_keywords):
            continue
        # 比赛段通常含 "vs" 或编号如 "周五001"
        if 'vs' not in header and not re.search(r'周[五六日]\d{3}', header):
            continue
        sections.append({
            'header': header,
            'lines': lines,
            'raw': part,
        })
    return sections


def lint_low_structure_weld(sections: list[dict], day: str | None = None) -> list[dict]:
    """
    低结构焊死倾向检测。
    draw_priority 场若写了「主胜」「客胜」「锁平」→ warn。
    """
    if day and day < STRUCTURE_GATE_DAY:
        return []

    warnings = []
    for sec in sections:
        lines = sec['lines']
        header = sec['header']

        # 提取 SP
        sp = None
        for line in lines:
            sp = parse_sp_line(line)
            if sp:
                break
        if not sp:
            continue

        tag = compute_structure_tag(sp[0], sp[1], sp[2])
        if tag != "draw_priority":
            continue

        # 检查是否焊死倾向
        for line in lines:
            if '方向｜倾向｜比分' in line or '方向｜' in line:
                # draw_priority 场禁止倾向主胜/客胜/锁平
                if re.search(r'倾向\s*主胜|倾向\s*客胜|锁\s*平|锁主|锁客', line):
                    warnings.append({
                        'rule': 'lint_low_structure_weld',
                        'severity': 'WARN',
                        'match': header,
                        'sp': sp,
                        'line': line.strip(),
                        'message': f"draw_priority 场焊死倾向: {line.strip()[:80]}"
                    })
                break
    return warnings


def lint_02_atom_text(sections: list[dict], day: str | None = None) -> list[dict]:
    """
    检查 02 对外句面是否含「防平」硬焊措辞。
    仅检测真正的硬焊：把防平与锁单写在一起，如「主胜（防平）」「锁主防平」。
    正常的「倾向主胜｜1-1 防」不算硬焊。
    """
    if day and day < STRUCTURE_GATE_DAY:
        return []

    warnings = []
    # 硬焊措辞：锁单与防平混写、或把防平当方向的一部分
    hard_weld_patterns = [
        r'主胜\s*[(（].*防平',      # 主胜（防平）
        r'客胜\s*[(（].*防平',      # 客胜（防平）
        r'锁[主客平].*防平',         # 锁主防平、锁客防平
        r'防平.*锁[主客平]',         # 防平锁主
        r'主胜防平|客胜防平|锁平防主|锁平防客',  # 无括号直接连写
    ]

    for sec in sections:
        lines = sec['lines']
        header = sec['header']

        for line in lines:
            for pat in hard_weld_patterns:
                if re.search(pat, line):
                    warnings.append({
                        'rule': 'lint_02_atom_text',
                        'severity': 'WARN',
                        'match': header,
                        'line': line.strip(),
                        'message': f"02 句面硬焊措辞: {line.strip()[:80]}"
                    })
                    break
    return warnings


def lint_02_must_direction(sections: list[dict], day: str | None = None) -> list[dict]:
    """
    4.22.3 方向必须给。检查每场是否有方向原子。
    """
    if day and day < DIR_MUST_DAY:
        return []

    warnings = []
    valid_atoms = ['锁主', '锁客', '锁平', '主不败', '客不败', '主胜', '客胜', '平局']

    for sec in sections:
        lines = sec['lines']
        header = sec['header']

        has_direction = False
        for line in lines:
            if '方向｜倾向｜比分' in line or '方向｜' in line:
                for atom in valid_atoms:
                    if atom in line:
                        has_direction = True
                        break
                break

        if not has_direction:
            warnings.append({
                'rule': 'lint_02_must_direction',
                'severity': 'ERROR',
                'match': header,
                'message': "方向原子缺失（禁止空槽/胶着）"
            })
    return warnings


def lint_lean_pack(sections: list[dict], day: str | None = None) -> list[dict]:
    """
    4.22.4 倾向必须 ∈ 允许集。
    主不败不得倾向客胜；客不败不得倾向主胜。
    """
    if day and day < LEAN_DAY:
        return []

    warnings = []
    for sec in sections:
        lines = sec['lines']
        header = sec['header']

        direction = None
        lean = None
        for line in lines:
            if '方向｜倾向｜比分' in line:
                # 提取方向
                if '主不败' in line:
                    direction = '主不败'
                elif '客不败' in line:
                    direction = '客不败'
                elif '锁主' in line or '主胜' in line and '倾向' not in line:
                    direction = '锁主'
                elif '锁客' in line or '客胜' in line and '倾向' not in line:
                    direction = '锁客'
                elif '锁平' in line:
                    direction = '锁平'

                # 提取倾向
                m = re.search(r'倾向\s*([^｜\|]+)', line)
                if m:
                    lean = m.group(1).strip()
                break

        if not direction or not lean:
            continue

        # 校验
        if direction == '主不败' and lean == '客胜':
            warnings.append({
                'rule': 'lint_lean_pack',
                'severity': 'ERROR',
                'match': header,
                'message': f"主不败场倾向客胜（违反允许集）: {lean}"
            })
        elif direction == '客不败' and lean == '主胜':
            warnings.append({
                'rule': 'lint_lean_pack',
                'severity': 'ERROR',
                'match': header,
                'message': f"客不败场倾向主胜（违反允许集）: {lean}"
            })
        elif direction in ('锁主', '锁客', '锁平') and lean not in ('不定', direction.replace('锁', '')):
            # 锁* 场倾向应与锁一致或写不定
            pass  # 放宽

    return warnings


def run_lint(filepath: str, day: str | None = None) -> dict:
    """运行全部 lint 规则，返回报告。"""
    sections = parse_sections(filepath)
    print(f"解析到 {len(sections)} 场比赛段")
    print(f"日闸: STRUCTURE_GATE={STRUCTURE_GATE_DAY}, DIR_MUST={DIR_MUST_DAY}, LEAN={LEAN_DAY}")
    print("-" * 60)

    all_warnings = []

    rules = [
        ("lint_low_structure_weld", lint_low_structure_weld),
        ("lint_02_atom_text", lint_02_atom_text),
        ("lint_02_must_direction", lint_02_must_direction),
        ("lint_lean_pack", lint_lean_pack),
        ("lint_deep_away_trap", lint_deep_away_trap),
    ]

    for name, fn in rules:
        w = fn(sections, day)
        all_warnings.extend(w)
        if w:
            print(f"\n[{name}] 发现 {len(w)} 个问题:")
            for item in w:
                print(f"  [{item['severity']}] {item['match'][:50]:50s} {item['message']}")
        else:
            print(f"\n[{name}] ✓ 通过")

    print("\n" + "=" * 60)
    total = len(all_warnings)
    errors = sum(1 for w in all_warnings if w['severity'] == 'ERROR')
    warns = sum(1 for w in all_warnings if w['severity'] == 'WARN')
    print(f"总计: {total} 个问题 (ERROR={errors}, WARN={warns})")

    return {
        'total': total,
        'errors': errors,
        'warnings': warns,
        'items': all_warnings,
    }



def lint_deep_away_trap(sections: list[dict], day: str | None = None) -> list[dict]:
    """
    深盘陷阱检测。
    客队是豪门且 SP_A <= 1.50 但无确认书/未降级 → warn。
    """
    TRAP_DAY = "2026-09-07"
    if day and day < TRAP_DAY:
        return []

    # 导入豪门检测
    import importlib.util
    import os
    _SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location("deep_away_trap", os.path.join(_SCRIPT_DIR, "deep_away_trap.py"))
    trap_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(trap_module)
    is_big_club = trap_module.is_big_club
    DEEP_AWAY_THRESHOLD = trap_module.DEEP_AWAY_THRESHOLD

    warnings = []
    for sec in sections:
        lines = sec['lines']
        header = sec['header']

        # 提取客队（从标题 "主队 vs 客队"）
        away = None
        if 'vs' in header:
            parts = header.split('vs')
            if len(parts) >= 2:
                away = parts[1].strip().split('｜')[0].strip()

        if not away or not is_big_club(away):
            continue

        # 提取 SP
        sp = None
        for line in lines:
            sp = parse_sp_line(line)
            if sp:
                break
        if not sp:
            continue

        sp_h, sp_d, sp_a = sp
        if sp_a > DEEP_AWAY_THRESHOLD:
            continue

        # 检查是否有确认书或降级
        has_trap = False
        has_downgrade = False
        for line in lines:
            if '深盘陷阱' in line or '确认书' in line:
                has_trap = True
            if 'dirty' in line.lower() or '降级' in line or '不进TOP2' in line:
                has_downgrade = True

        if has_trap and has_downgrade:
            continue

        warnings.append({
            'rule': 'lint_deep_away_trap',
            'severity': 'WARN',
            'match': header,
            'sp_a': sp_a,
            'away': away,
            'message': f"深盘豪门客场未做确认书/未降级: {away} SP_A={sp_a:.2f}"
        })

    return warnings

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="V17.4.23 日闸 lint 工具")
    parser.add_argument('file', help='草稿 markdown 文件路径')
    parser.add_argument('--day', help='日期阈值 (YYYY-MM-DD)，小于此日的旧稿不检查新规则', default=None)
    args = parser.parse_args()


