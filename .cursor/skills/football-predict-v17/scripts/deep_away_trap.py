#!/usr/bin/env python3
"""
deep_away_trap.py — V17.4.23 深盘陷阱确认书

功能：
1. 检测客队是否为豪门 + 是否有疲劳/轮换信号
2. 输出确认书（战意衰减 + 客场疲劳双模块）
3. 若确认书「不干净」→ 建议降级方向/倾向

用法：
    python3 deep_away_trap.py --away "皇马" --sp_a 1.28 --euro_match "下周中欧冠" --rotation "可能轮换"

豪门名单（硬编码）：
- 英超：曼城、利物浦、阿森纳、曼联、切尔西
- 西甲：皇马、巴塞罗那、巴萨、马竞、马德里竞技
- 德甲：拜仁、多特蒙德、勒沃库森
- 意甲：尤文图斯、尤文、国际米兰、国米、AC米兰
- 法甲：巴黎圣日耳曼、巴黎、PSG
"""

import argparse
from typing import List, Dict, Optional

# === 豪门名单 ===
BIG_CLUBS = {
    '曼城', '利物浦', '阿森纳', '曼联', '切尔西',
    '皇马', '皇家马德里', '巴塞罗那', '巴萨', '马竞', '马德里竞技',
    '拜仁', '拜仁慕尼黑', '多特蒙德', '勒沃库森',
    '尤文图斯', '尤文', '国际米兰', '国米', 'AC米兰',
    '巴黎圣日耳曼', '巴黎', 'PSG',
}

# === 深盘阈值 ===
DEEP_AWAY_THRESHOLD = 1.50  # 客胜赔 ≤ 此值视为深盘


def is_big_club(club_name: str) -> bool:
    """检查俱乐部是否在豪门名单中。"""
    for bc in BIG_CLUBS:
        if bc in club_name:
            return True
    return False


def detect_trap_signals(
    away_club: str,
    sp_a: float,
    euro_match: Optional[str] = None,
    rotation: Optional[str] = None,
    away_fatigue: Optional[str] = None,
    home_motivation: Optional[str] = None,
) -> Dict:
    """
    深盘陷阱信号检测。

    返回：
        {
            'is_big_club': bool,
            'is_deep': bool,           # SP_A ≤ 1.50
            'signals': List[str],      # 检测到的风险信号
            'score': int,              # 风险分数（0-5）
            'verdict': str,            # 结论：clean / caution / dirty
            'recommendation': str,     # 建议动作
        }
    """
    signals = []
    score = 0

    is_big = is_big_club(away_club)
    is_deep = sp_a <= DEEP_AWAY_THRESHOLD

    if not is_big:
        return {
            'is_big_club': False,
            'is_deep': is_deep,
            'signals': [],
            'score': 0,
            'verdict': 'clean',
            'recommendation': '非豪门客场，不触发深盘陷阱检查',
        }

    # === 战意衰减探测器 ===
    if euro_match and ('欧冠' in euro_match or '欧联' in euro_match or '欧战' in euro_match):
        signals.append(f'周中有欧战：{euro_match}')
        score += 2

    if rotation and ('轮换' in rotation or '替补' in rotation or ' rested' in rotation):
        signals.append(f'轮换信号：{rotation}')
        score += 1

    # === 客场疲劳计算器 ===
    if away_fatigue and ('疲劳' in away_fatigue or '连客' in away_fatigue or '飞行' in away_fatigue):
        signals.append(f'客场疲劳：{away_fatigue}')
        score += 1

    # === 主队战意 ===
    if home_motivation and ('保级' in home_motivation or '复仇' in home_motivation or '首胜' in home_motivation):
        signals.append(f'主队战意强：{home_motivation}')
        score += 1

    # ===  verdict ===
    if score >= 3:
        verdict = 'dirty'
        recommendation = f'深盘陷阱风险高（{score}/5）：方向降级为"主不败/客不败"，单子倾向写"不定"，研究星封顶★★★☆☆，不进TOP2'
    elif score >= 1:
        verdict = 'caution'
        recommendation = f'深盘陷阱风险中（{score}/5）：须写反剧本收据，防格必须含1-0/2-1主队胜，旁注挂主队逆转'
    else:
        verdict = 'clean'
        if is_deep:
            recommendation = '深盘但无疲劳信号，正常分析，仍须写反剧本收据（V17.4.20硬性要求）'
        else:
            recommendation = '非深盘豪门客场，正常分析'

    return {
        'is_big_club': is_big,
        'is_deep': is_deep,
        'signals': signals,
        'score': score,
        'verdict': verdict,
        'recommendation': recommendation,
    }


def format_confirmation(signal_result: Dict) -> str:
    """格式化确认书输出。"""
    lines = []
    lines.append("=" * 50)
    lines.append("【深盘陷阱确认书】")
    lines.append("=" * 50)
    lines.append(f"豪门检测：{'✓ 是豪门' if signal_result['is_big_club'] else '✗ 非豪门'}")
    lines.append(f"深盘检测：{'✓ SP≤1.50' if signal_result['is_deep'] else '✗ SP>1.50'}")
    lines.append(f"风险分数：{signal_result['score']}/5")
    lines.append(f"结论：{signal_result['verdict'].upper()}")
    lines.append("")

    if signal_result['signals']:
        lines.append("【风险信号】")
        for sig in signal_result['signals']:
            lines.append(f"  ⚠️ {sig}")
        lines.append("")

    lines.append("【建议动作】")
    lines.append(f"  {signal_result['recommendation']}")
    lines.append("=" * 50)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description='深盘陷阱确认书')
    parser.add_argument('--away', required=True, help='客队名称')
    parser.add_argument('--sp_a', type=float, required=True, help='客胜赔')
    parser.add_argument('--euro_match', default=None, help='周中欧战信息')
    parser.add_argument('--rotation', default=None, help='轮换信号')
    parser.add_argument('--away_fatigue', default=None, help='客场疲劳')
    parser.add_argument('--home_motivation', default=None, help='主队战意')
    args = parser.parse_args()

    result = detect_trap_signals(
        away_club=args.away,
        sp_a=args.sp_a,
        euro_match=args.euro_match,
        rotation=args.rotation,
        away_fatigue=args.away_fatigue,
        home_motivation=args.home_motivation,
    )

    print(format_confirmation(result))


if __name__ == '__main__':
    # 默认演示：毕尔巴鄂 vs 马竞
    import sys
    if len(sys.argv) == 1:
        print("=== 演示：毕尔巴鄂 vs 马竞 ===")
        sys.argv = ['', '--away', '马竞', '--sp_a', '2.16',
                    '--euro_match', '下周中欧冠客战利物浦',
                    '--rotation', 'Simeone可能轮换',
                    '--home_motivation', '毕尔巴鄂上轮2-0开胡，主场要延续胜势']
    main()
