#!/usr/bin/env python3
"""深让豪门客场风险标签；不自动修改方向、概率、比分或出票。"""
import argparse
from typing import Dict, Optional

BIG_CLUBS = {
    '曼城', '利物浦', '阿森纳', '曼联', '切尔西',
    '皇马', '皇家马德里', '巴塞罗那', '巴萨', '马竞', '马德里竞技',
    '拜仁', '拜仁慕尼黑', '多特蒙德', '勒沃库森',
    '尤文图斯', '尤文', '国际米兰', '国米', 'AC米兰',
    '巴黎圣日耳曼', '巴黎', 'PSG',
    '利雅胜利', '利雅得胜利', '艾納斯', 'Al Nassr',
    '利雅得新月', '希拉尔', 'Al Hilal',
    '吉达联合', '伊蒂哈德', 'Al Ittihad',
    '吉达国民', '阿尔阿赫利', 'Al Ahli',
}
DEEP_AWAY_THRESHOLD = 1.50
ASIAN_HANDICAP_THRESHOLD = 0.75


def is_big_club(club_name: str) -> bool:
    return any(club in club_name for club in BIG_CLUBS)


def detect_trap_signals(
    away_club: str,
    sp_a: float,
    asian_handicap: Optional[float] = None,
    market_divergence: Optional[str] = None,
    euro_match: Optional[str] = None,
    rotation: Optional[str] = None,
    away_fatigue: Optional[str] = None,
    home_motivation: Optional[str] = None,
) -> Dict:
    signals = []
    is_big = is_big_club(away_club)
    is_deep_sp = is_big and sp_a <= DEEP_AWAY_THRESHOLD
    is_deep_ah = is_big and asian_handicap is not None and asian_handicap >= ASIAN_HANDICAP_THRESHOLD
    is_deep_div = bool(market_divergence)
    if is_deep_sp:
        signals.append(f'豪门客胜低SP：{sp_a:.2f}')
    if is_deep_ah:
        signals.append(f'豪门客场深让：{asian_handicap}')
    if is_deep_div:
        signals.append(f'跨市场差异：{market_divergence}')
    if euro_match and any(word in euro_match for word in ('欧冠', '欧联', '欧战')):
        signals.append(f'邻近欧战：{euro_match}')
    if rotation and any(word in rotation for word in ('轮换', '替补', 'rested')):
        signals.append(f'轮换线索：{rotation}')
    if away_fatigue and any(word in away_fatigue for word in ('疲劳', '连客', '飞行')):
        signals.append(f'客场体能线索：{away_fatigue}')
    if home_motivation and any(word in home_motivation for word in ('保级', '复仇', '首胜')):
        signals.append(f'主队战意线索：{home_motivation}')
    return {
        'is_big_club': is_big,
        'is_deep': is_deep_sp or is_deep_ah or is_deep_div,
        'signals': signals,
        'risk_level': '提示' if signals else '无',
        'recommendation': (
            '仅作风险标记；核对证据后进入统一λ与保守概率，不自动降级或改比分'
            if signals else '未触发该风险标签，按统一概率流程分析'
        ),
    }


def format_confirmation(result: Dict) -> str:
    lines = [
        '【深盘风险标记】',
        f"豪门检测={'是' if result['is_big_club'] else '否'}｜深盘检测={'是' if result['is_deep'] else '否'}",
        f"风险级别={result['risk_level']}（非方向结论）",
    ]
    lines.extend(f'信号={signal}' for signal in result['signals'])
    lines.append(result['recommendation'])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--away', required=True)
    parser.add_argument('--sp_a', type=float, required=True)
    parser.add_argument('--asian_handicap', type=float)
    parser.add_argument('--market_divergence')
    parser.add_argument('--euro_match')
    parser.add_argument('--rotation')
    parser.add_argument('--away_fatigue')
    parser.add_argument('--home_motivation')
    args = parser.parse_args()
    print(format_confirmation(detect_trap_signals(
        away_club=args.away,
        sp_a=args.sp_a,
        asian_handicap=args.asian_handicap,
        market_divergence=args.market_divergence,
        euro_match=args.euro_match,
        rotation=args.rotation,
        away_fatigue=args.away_fatigue,
        home_motivation=args.home_motivation,
    )))


if __name__ == '__main__':
    main()
