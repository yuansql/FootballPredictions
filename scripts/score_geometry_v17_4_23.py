#!/usr/bin/env python3
"""
score_geometry.py — V17.4.23 比分覆盖最大化（补偿后 Top3）

功能：
1. 从情景路径提取权重 Top3
2. 按情报信号做三桶补偿（低估进球/高估进球/逆转局）
3. 输出补偿后的公开三格（主/次/防）

用法：
    python3 score_geometry.py --paths "path_A=1-0,w=0.35;path_B=2-1,w=0.25;path_C=1-1,w=0.25;path_D=0-1,w=0.15" \
        --signals "HIGH_SCORING,HOME_REVENGE"

三桶补偿规则：
- 低估进球补偿（HIGH_SCORING）：双方近5场均总球≥2.5 → Top3 必须包含≥3球选项
- 高估进球补偿（LOW_SCORING）：双方近5场均总球≤1.5 → 主推给0-0/1-0
- 逆转局补偿（REVERSAL）：ht_path_B含对方先破门且w≥0.15 → 防格给逆转分
"""

import re
import sys
import argparse
from typing import List, Tuple, Dict

# === 补偿规则常量 ===
HIGH_SCORING_THRESHOLD = 2.5   # 近5场场均总球≥此值 → 高估进球风险
LOW_SCORING_THRESHOLD = 1.5    # 近5场场均总球≤此值 → 低估进球风险
REVERSAL_HT_WEIGHT = 0.15      # 半场逆转路径权重阈值
COMPENSATION_SCORES = {
    'HIGH_SCORING': ['2-2', '3-1', '1-3', '2-3', '3-2', '4-1', '1-4'],  # ≥4球
    'LOW_SCORING': ['0-0', '1-0', '0-1', '1-1'],                       # ≤2球
    'REVERSAL_HOME': ['2-1', '3-1', '2-0', '3-2', '4-2'],              # 主队逆转
    'REVERSAL_AWAY': ['1-2', '1-3', '0-2', '2-3', '2-4'],              # 客队逆转
}


def parse_paths(paths_str: str) -> List[Tuple[str, str, float]]:
    """
    解析路径字符串。
    格式："path_A=1-0,w=0.35;path_B=2-1,w=0.25"
    返回：[(path_name, score, weight), ...]
    """
    paths = []
    for seg in paths_str.split(';'):
        seg = seg.strip()
        if not seg:
            continue
        # 匹配 path_A=1-0,w=0.35 或 path_A=主队小胜|weight=0.35|终场=1-0
        score_match = re.search(r'[=:](\d+-\d+)', seg)
        weight_match = re.search(r'[wW]=(\d+\.?\d*)', seg)
        if score_match and weight_match:
            path_name = seg.split('=')[0].strip()
            score = score_match.group(1)
            weight = float(weight_match.group(1))
            paths.append((path_name, score, weight))
    return paths


def parse_signals(signals_str: str) -> List[str]:
    """解析信号标签，逗号分隔。"""
    return [s.strip().upper() for s in signals_str.split(',') if s.strip()]


def get_score_family(score: str, direction: str) -> str:
    """
    判断比分属于哪一族。
    返回：'home_win' | 'draw' | 'away_win'
    """
    h, a = map(int, score.split('-'))
    if h > a:
        return 'home_win'
    elif h < a:
        return 'away_win'
    else:
        return 'draw'


def get_total_goals(score: str) -> int:
    """计算总进球数。"""
    h, a = map(int, score.split('-'))
    return h + a


def compensate_top3(
    paths: List[Tuple[str, str, float]],
    signals: List[str],
    direction: str = '主不败',
    lean: str = '不定'
) -> Dict:
    """
    核心函数：补偿后 Top3 选取。

    参数：
        paths: [(path_name, score, weight), ...]
        signals: ['HIGH_SCORING', 'REVERSAL_HOME', ...]
        direction: 方向原子（主不败/客不败/锁主/锁客）
        lean: 单子倾向（主胜/客胜/平/不定）

    返回：
        {
            'primary': str,      # 主推
            'secondary': str,    # 次选
            'defense': str,      # 防格
            'side': List[str],   # 旁注
            'compensation_applied': List[str],  # 应用的补偿规则
            'original_top3': List[str],  # 原始权重Top3
        }
    """
    # 按权重排序
    sorted_paths = sorted(paths, key=lambda x: x[2], reverse=True)
    original_scores = [p[1] for p in sorted_paths[:3]]

    compensation_applied = []
    candidate_pool = [p[1] for p in sorted_paths]  # 所有候选比分

    # === 补偿1：低估进球（HIGH_SCORING）===
    # 问题：情报层判断进球多，但AI权重池开口低 → 必须强制扩口
    # 触发：HIGH_SCORING 信号存在（情报层已标记双方火力强/联赛开放）
    # 动作：无论当前Top3如何，强制把≥4球比分加入候选池
    if 'HIGH_SCORING' in signals:
        for comp_score in COMPENSATION_SCORES['HIGH_SCORING']:
            if comp_score not in candidate_pool:
                candidate_pool.append(comp_score)
        compensation_applied.append('HIGH_SCORING')

    # === 补偿2：高估进球（LOW_SCORING）===
    # 问题：情报层判断进球少，但AI权重池偏高 → 必须强制收窄
    # 触发：LOW_SCORING 信号存在（情报层已标记双方进攻低迷/教练保守）
    # 动作：强制把≤2球比分加入候选池
    if 'LOW_SCORING' in signals:
        for comp_score in COMPENSATION_SCORES['LOW_SCORING']:
            if comp_score not in candidate_pool:
                candidate_pool.append(comp_score)
        compensation_applied.append('LOW_SCORING')

    # === 补偿3：逆转局 ===
    if 'REVERSAL_HOME' in signals:
        has_reversal = any(s in COMPENSATION_SCORES['REVERSAL_HOME'] for s in original_scores)
        if not has_reversal:
            for comp_score in COMPENSATION_SCORES['REVERSAL_HOME']:
                if comp_score not in candidate_pool:
                    candidate_pool.append(comp_score)
            compensation_applied.append('REVERSAL_HOME')
    elif 'REVERSAL_AWAY' in signals:
        has_reversal = any(s in COMPENSATION_SCORES['REVERSAL_AWAY'] for s in original_scores)
        if not has_reversal:
            for comp_score in COMPENSATION_SCORES['REVERSAL_AWAY']:
                if comp_score not in candidate_pool:
                    candidate_pool.append(comp_score)
            compensation_applied.append('REVERSAL_AWAY')

    # === 重新选取 Top3 ===
    # 策略：优先保留原权重最高的，然后填充补偿项
    # 但防格必须多样化（不能三格同族）

    # 按方向/倾向确定主次族
    if lean == '主胜' or direction == '锁主':
        primary_family = 'home_win'
        defense_family = 'draw'  # 防格给平
    elif lean == '客胜' or direction == '锁客':
        primary_family = 'away_win'
        defense_family = 'draw'
    elif lean == '平' or direction == '锁平':
        primary_family = 'draw'
        defense_family = 'home_win'  # 防格给主胜
    else:  # 不定 / 主不败 / 客不败
        primary_family = None  # 权重池混装
        defense_family = None

    # 从候选池选三格
    selected = []
    side = []

    # 第一格：权重最高
    if sorted_paths:
        selected.append(sorted_paths[0][1])

    # 第二格：权重次高，且与第一格不同族（如果可能）
    for p in sorted_paths[1:]:
        if len(selected) >= 2:
            break
        if primary_family and get_score_family(p[1], direction) != get_score_family(selected[0], direction):
            selected.append(p[1])
            break
    if len(selected) < 2:
        for p in sorted_paths[1:]:
            if p[1] not in selected:
                selected.append(p[1])
                break

    # 第三格（防格）：补偿优先 + 多样化
    # 先尝试补偿分
    compensation_scores = []
    if 'HIGH_SCORING' in compensation_applied:
        compensation_scores.extend(COMPENSATION_SCORES['HIGH_SCORING'])
    if 'LOW_SCORING' in compensation_applied:
        compensation_scores.extend(COMPENSATION_SCORES['LOW_SCORING'])
    if 'REVERSAL_HOME' in compensation_applied:
        compensation_scores.extend(COMPENSATION_SCORES['REVERSAL_HOME'])
    if 'REVERSAL_AWAY' in compensation_applied:
        compensation_scores.extend(COMPENSATION_SCORES['REVERSAL_AWAY'])

    # 选一个补偿分作为防格（如果还没选过）
    defense = None
    for cs in compensation_scores:
        if cs not in selected:
            # 检查是否多样化
            if defense_family and get_score_family(cs, direction) == defense_family:
                defense = cs
                break
            elif not defense_family:
                defense = cs
                break

    # 如果没找到补偿防格，从原权重池找
    if not defense:
        for p in sorted_paths:
            if p[1] not in selected:
                defense = p[1]
                break

    if defense and defense not in selected:
        selected.append(defense)

    # 旁注：其他补偿分
    for cs in compensation_scores:
        if cs not in selected and cs not in side:
            side.append(cs)

    # 如果还不足3格，从候选池补
    while len(selected) < 3:
        for c in candidate_pool:
            if c not in selected:
                selected.append(c)
                break
        else:
            break

    return {
        'primary': selected[0] if len(selected) > 0 else None,
        'secondary': selected[1] if len(selected) > 1 else None,
        'defense': selected[2] if len(selected) > 2 else None,
        'side': side[:2],  # 最多2个旁注
        'compensation_applied': compensation_applied,
        'original_top3': original_scores,
        'all_candidates': candidate_pool,
    }


def main():
    parser = argparse.ArgumentParser(description='V17.4.23 比分覆盖最大化')
    parser.add_argument('--paths', required=True, help='路径字符串，格式：path_A=1-0,w=0.35;path_B=2-1,w=0.25')
    parser.add_argument('--signals', default='', help='信号标签，逗号分隔：HIGH_SCORING,LOW_SCORING,REVERSAL_HOME')
    parser.add_argument('--direction', default='主不败', help='方向原子')
    parser.add_argument('--lean', default='不定', help='单子倾向')
    args = parser.parse_args()

    paths = parse_paths(args.paths)
    signals = parse_signals(args.signals)

    print(f"输入路径: {paths}")
    print(f"信号: {signals}")
    print(f"方向: {args.direction}, 倾向: {args.lean}")
    print("-" * 50)

    result = compensate_top3(paths, signals, args.direction, args.lean)

    print(f"原始权重 Top3: {result['original_top3']}")
    print(f"应用补偿: {result['compensation_applied']}")
    print(f"补偿后候选池: {result['all_candidates']}")
    print(f"公开三格: 主推={result['primary']}, 次选={result['secondary']}, 防={result['defense']}")
    print(f"旁注: {result['side']}")


if __name__ == '__main__':
    # 默认演示：纽卡斯尔 vs 伯恩茅斯（实际2-2，旧预测1-0/2-1/1-1）
    if len(sys.argv) == 1:
        print("=== 演示：纽卡斯尔 vs 伯恩茅斯（实际2-2）===")
        print("旧预测 Top3: 1-0 / 2-1 / 1-1（最大3球，实际4球 → 低估进球）")
        print()
        demo_paths = "path_A=主队小胜,w=0.35,终场=1-0;path_B=主队多一球,w=0.25,终场=2-1;path_C=收平,w=0.25,终场=1-1;path_D=客队偷胜,w=0.15,终场=1-2"
        demo_signals = "HIGH_SCORING"
        sys.argv = ['', '--paths', demo_paths, '--signals', demo_signals, '--direction', '主不败', '--lean', '不定']

    main()
