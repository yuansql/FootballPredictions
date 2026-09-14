#!/usr/bin/env python3
"""
backtest_structure_gate.py — 低结构平优先闸历史回测

输入：
  - 预测文件（含 SP + 方向/倾向/比分）
  - 复盘文件（含实际比分）

输出：
  - docs/backtest/structure_gate_backtest.md

用法：
    python3 backtest_structure_gate.py \
        --predictions <预测文件.txt> \
        --backtest <复盘文件.md> \
        --out <输出文件.md>
"""

import sys
import os
import re
import argparse
from datetime import datetime

# 导入 structure_gate
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
import importlib.util
spec = importlib.util.spec_from_file_location("structure_gate", os.path.join(_SCRIPT_DIR, "structure_gate.py"))
structure_gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(structure_gate)

compute_structure_tag = structure_gate.compute_structure_tag
get_enforced_direction = structure_gate.get_enforced_direction
parse_sp_line = structure_gate.parse_sp_line


def parse_predictions(filepath: str) -> list[dict]:
    """解析预测文件，提取每场比赛的 SP、方向、倾向。"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    matches = []
    sections = re.split(r'\n## ', content)

    for sec in sections:
        lines = sec.strip().split('\n')
        if not lines:
            continue

        header = lines[0].strip().lstrip('#').strip()
        if 'vs' not in header and not re.search(r'周[五六日]\d{3}', header):
            continue

        # 提取 SP
        sp = None
        for line in lines:
            sp = parse_sp_line(line)
            if sp:
                break

        # 提取方向和倾向
        direction = None
        lean = None
        scores = []
        for line in lines:
            if '方向｜倾向｜比分' in line:
                if '主不败' in line:
                    direction = '主不败'
                elif '客不败' in line:
                    direction = '客不败'
                elif '锁主' in line or ('主胜' in line and '倾向' not in line):
                    direction = '主胜'
                elif '锁客' in line or ('客胜' in line and '倾向' not in line):
                    direction = '客胜'
                elif '锁平' in line:
                    direction = '平'

                m = re.search(r'倾向\s*([^｜\|]+)', line)
                if m:
                    lean = m.group(1).strip()

                # 提取比分
                score_nums = re.findall(r'\*\*(\d+-\d+)\*\*', line)
                scores = score_nums
                break

        matches.append({
            'header': header,
            'sp': sp,
            'direction': direction,
            'lean': lean,
            'scores': scores,
        })

    return matches


def parse_backtest_results(filepath: str) -> dict[str, tuple]:
    """解析复盘文件，返回 {比赛名: (实际比分, 方向是否命中, 倾向是否命中)}。"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    results = {}
    # 匹配表格行
    # | # | 场次 | 预测方向 | 预测倾向 | ... | 实际比分 | 方向 | 倾向 | ... |
    table_pattern = re.compile(
        r'\|\s*\d+\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|'
        r'[^|]*\|\s*\*\*(\d+-\d+)\*\*\s*\|\s*([✓✗])\s*\|\s*([✓✗])\s*\|'
    )

    for m in table_pattern.finditer(content):
        match_name = m.group(1).strip()
        pred_dir = m.group(2).strip()
        pred_lean = m.group(3).strip()
        actual_score = m.group(4)
        dir_hit = m.group(5) == '✓'
        lean_hit = m.group(6) == '✓'

        # 用简化名做 key
        key = match_name.replace(' ', '').replace('vs', ' ')
        results[key] = {
            'actual_score': actual_score,
            'dir_hit': dir_hit,
            'lean_hit': lean_hit,
            'pred_dir': pred_dir,
            'pred_lean': pred_lean,
        }

    return results


def normalize_key(header: str) -> str:
    """归一化比赛名用于匹配。"""
    # 去掉前缀如 "周五001｜"
    cleaned = re.sub(r'^周[五六日]\d{3}｜', '', header)
    # 去掉联赛后缀
    cleaned = re.sub(r'｜[^｜]+$', '', cleaned)
    return cleaned.replace(' ', '').replace('vs', ' ')


def run_backtest(pred_file: str, backtest_file: str, out_file: str) -> None:
    predictions = parse_predictions(pred_file)
    backtest = parse_backtest_results(backtest_file)

    # 匹配预测与复盘
    matched = []
    for pred in predictions:
        key = normalize_key(pred['header'])
        bt = None
        for bt_key, bt_val in backtest.items():
            if key in bt_key or bt_key in key:
                bt = bt_val
                break

        if not bt:
            continue

        sp = pred['sp']
        if not sp:
            continue

        tag = compute_structure_tag(sp[0], sp[1], sp[2])
        enforced_dir, enforced_lean = get_enforced_direction(sp[0], sp[1], sp[2])

        matched.append({
            'header': pred['header'],
            'sp': sp,
            'tag': tag,
            'original_dir': pred['direction'],
            'original_lean': pred['lean'],
            'enforced_dir': enforced_dir,
            'enforced_lean': enforced_lean,
            'actual_score': bt['actual_score'],
            'original_dir_hit': bt['dir_hit'],
            'original_lean_hit': bt['lean_hit'],
        })

    # 统计
    draw_priority_matches = [m for m in matched if m['tag'] == 'draw_priority']
    would_change_lean = [
        m for m in draw_priority_matches
        if m['original_lean'] != '不定' and m['enforced_lean'] == '不定'
    ]

    # 计算启用闸后的变化
    lean_improved = 0
    lean_worsened = 0
    dir_changed = 0
    dir_improved = 0
    dir_worsened = 0

    for m in draw_priority_matches:
        actual = m['actual_score']
        home_goals, away_goals = map(int, actual.split('-'))

        # 方向变化统计
        if m['enforced_dir'] != m['original_dir']:
            dir_changed += 1
            # 评估新方向的命中
            if m['enforced_dir'] == '主不败':
                new_dir_hit = home_goals >= away_goals
            elif m['enforced_dir'] == '客不败':
                new_dir_hit = away_goals >= home_goals
            else:
                new_dir_hit = m['original_dir_hit']

            if new_dir_hit and not m['original_dir_hit']:
                dir_improved += 1
            elif not new_dir_hit and m['original_dir_hit']:
                dir_worsened += 1

        # 倾向变化统计（仅对倾向被强制改的场次）
        if m in would_change_lean:
            if m['enforced_dir'] == '主不败':
                new_lean_hit = home_goals >= away_goals
            elif m['enforced_dir'] == '客不败':
                new_lean_hit = away_goals >= home_goals
            else:
                new_lean_hit = m['original_lean_hit']

            if new_lean_hit and not m['original_lean_hit']:
                lean_improved += 1
            elif not new_lean_hit and m['original_lean_hit']:
                lean_worsened += 1

    # 生成报告
    report = f"""# 低结构平优先闸回测报告

> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}
> 预测文件：`{os.path.basename(pred_file)}`
> 复盘文件：`{os.path.basename(backtest_file)}`

## 一、总体统计

| 指标 | 数值 |
|------|------|
| 总匹配场次 | {len(matched)} |
| draw_priority 触发 | {len(draw_priority_matches)} |
| 倾向被强制改为"不定" | {len(would_change_lean)} |
| 倾向改善（miss→hit） | {lean_improved} |
| 倾向恶化（hit→miss） | {lean_worsened} |
| 方向原子变化 | {dir_changed} |

## 二、draw_priority 触发场次详情

"""

    for m in draw_priority_matches:
        changed = "🔧 强制改" if m in would_change_lean else "✓ 已合规"
        report += f"""### {m['header']}

- SP：{m['sp'][0]:.2f} / {m['sp'][1]:.2f} / {m['sp'][2]:.2f}
- 结构标签：{m['tag']}
- 原预测：{m['original_dir']}｜倾向 {m['original_lean']}
- 强制输出：{m['enforced_dir']}｜倾向 {m['enforced_lean']}
- 实际比分：**{m['actual_score']}**
- 原方向命中：{'✓' if m['original_dir_hit'] else '✗'}
- 原倾向命中：{'✓' if m['original_lean_hit'] else '✗'}
- **{changed}**

"""

    report += f"""## 三、关键发现

### 3.1 倾向焊死问题

在 {len(draw_priority_matches)} 场 draw_priority 比赛中，{len(would_change_lean)} 场原预测焊死了倾向（主胜/客胜），而结构要求写"不定"。

### 3.2 若启用闸后的变化

"""

    if lean_improved > 0:
        report += f'- **倾向改善 {lean_improved} 场**：原"主胜/客胜"焊死导致 miss，改为"不定"后覆盖平局/反胜，倾向命中。\n'
    if lean_worsened > 0:
        report += f'- 倾向恶化 {lean_worsened} 场：原焊死碰巧 hit，改为"不定"后反而 miss（小概率）。\n'
    if lean_improved == 0 and lean_worsened == 0:
        report += "- 本样本中启用闸后倾向命中数无变化（需要更大样本验证）。\n"

    report += f"""
### 3.3 阈值回顾

当前 draw_priority 触发条件：
1. 双方 SP > 2.0 且 |SP_H - SP_A| < 1.5
2. SP_D < 3.0
3. max(SP_H, SP_A) / min(SP_H, SP_A) < 1.8

触发率：{len(draw_priority_matches)}/{len(matched)} = {len(draw_priority_matches)/len(matched)*100:.1f}%

## 四、建议

"""

    if lean_improved >= lean_worsened:
        report += "- 启用 `draw_priority` 闸后倾向命中率预期提升，建议保留当前阈值。\n"
    else:
        report += "- 本样本中启用闸效果不明显，建议收集更多样本或调整阈值。\n"

    report += """- 重点监控：draw_priority 场次的实际平局率是否显著高于高结构场次。
- 后续迭代：当 draw_priority 样本 ≥30 场时，做卡方检验验证有效性。
"""

    # 写入文件
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"回测报告已写入：{out_file}")
    print(f"draw_priority 触发 {len(draw_priority_matches)} 场，倾向强制改 {len(would_change_lean)} 场")
    print(f"预期倾向改善 {lean_improved} 场，恶化 {lean_worsened} 场")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="低结构平优先闸历史回测")
    parser.add_argument('--predictions', required=True, help='预测文件路径')
    parser.add_argument('--backtest', required=True, help='复盘文件路径')
    parser.add_argument('--out', default=os.path.join(_SCRIPT_DIR, '..', 'docs', 'backtest', 'structure_gate_backtest.md'),
                        help='输出报告路径')
    args = parser.parse_args()

    run_backtest(args.predictions, args.backtest, args.out)
