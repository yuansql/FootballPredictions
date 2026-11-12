#!/usr/bin/env python3
"""由 λ 区间角点导出保守概率。

保守概率不是手工下调的常数，而是 λ 不确定度的函数：在 λ_H/λ_A 区间的四个角点
各跑一次同一比分矩阵，对每个玩法的每个选项取最差（最小）概率。

这样不同玩法自动得到不同折扣——总进球只关心 λ 总量、对主客分配不敏感，
让球对分配极敏感——手工统一打折做不到这个区分。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from probability_model import (  # noqa: E402
    handicap_probabilities,
    result_probabilities,
    score_matrix,
    total_goals_probabilities,
)

RESULT_LABELS = ('主胜', '平', '客胜')
CORNER_LABELS = ('λH低/λA低', 'λH低/λA高', 'λH高/λA低', 'λH高/λA高')


def corner_points(lambda_h, lambda_a, h_lo, h_hi, a_lo, a_hi):
    """校验并返回四个角点。点估计必须落在区间内，否则区间写错了。"""
    values = {'λ_H': lambda_h, 'λ_A': lambda_a, 'h_lo': h_lo, 'h_hi': h_hi, 'a_lo': a_lo, 'a_hi': a_hi}
    for name, value in values.items():
        value = float(value)
        if not value > 0:
            raise ValueError(f'{name} 须为正数，得到 {value}')
        values[name] = value
    if not values['h_lo'] <= values['λ_H'] <= values['h_hi']:
        raise ValueError(f'λ_H={values["λ_H"]} 不在区间 [{values["h_lo"]},{values["h_hi"]}] 内')
    if not values['a_lo'] <= values['λ_A'] <= values['a_hi']:
        raise ValueError(f'λ_A={values["λ_A"]} 不在区间 [{values["a_lo"]},{values["a_hi"]}] 内')
    return (
        (values['h_lo'], values['a_lo']),
        (values['h_lo'], values['a_hi']),
        (values['h_hi'], values['a_lo']),
        (values['h_hi'], values['a_hi']),
    )


def _elementwise_min(vectors):
    """各向量长度可能不同（动态截断）；缺失位按 0.0 处理，误差上界为尾部容差。"""
    width = max(len(v) for v in vectors)
    return tuple(min((v[i] if i < len(v) else 0.0) for v in vectors) for i in range(width))


def conservative_model(lambda_h, lambda_a, h_lo, h_hi, a_lo, a_hi, tail_tolerance=1e-4):
    points = corner_points(lambda_h, lambda_a, h_lo, h_hi, a_lo, a_hi)
    models = [score_matrix(h, a, tail_tolerance) for h, a in points]
    per_corner = [result_probabilities(m) for m in models]
    worst = [min(range(len(per_corner)), key=lambda k: per_corner[k][i]) for i in range(3)]
    return {
        'points': points,
        'models': models,
        'result': _elementwise_min(per_corner),
        'result_per_corner': tuple(per_corner),
        'result_worst_corner': tuple(worst),
        'total_goals': _elementwise_min([total_goals_probabilities(m) for m in models]),
    }


def conservative_handicap(model, home_handicap):
    return _elementwise_min([handicap_probabilities(m, home_handicap) for m in model['models']])


def conservative_top_scores(model, limit=3):
    matrices = [m['matrix'] for m in model['models']]
    height = max(len(m) for m in matrices)
    width = max(len(row) for m in matrices for row in m)
    cells = []
    for i in range(height):
        for j in range(width):
            values = [
                m[i][j] if i < len(m) and j < len(m[i]) else 0.0
                for m in matrices
            ]
            cells.append((i, j, min(values)))
    return tuple(sorted(cells, key=lambda item: item[2], reverse=True)[:limit])


def joint_conservative(probabilities, rho=1.0):
    """多腿联合保守概率 = 独立乘积 × ρ。

    ρ 是相关性折扣，必须由 tickets-ledger 标定；未标定时调用方须显式标注，
    不得把猜测值伪装成估计结果。
    """
    rho = float(rho)
    if not 0 < rho <= 1:
        raise ValueError('ρ 须在 (0,1]；大于 1 不是保守调整')
    product = 1.0
    for p in probabilities:
        p = float(p)
        if not 0 <= p <= 1:
            raise ValueError('概率须在 0..1')
        product *= p
    return product * rho


def _parse_interval(text, name):
    parts = [p.strip() for p in str(text).replace('，', ',').split(',') if p.strip()]
    if len(parts) != 2:
        raise ValueError(f'{name} 须写成 lo,hi 两个数，得到 {text!r}')
    return float(parts[0]), float(parts[1])


def main(argv=None):
    parser = argparse.ArgumentParser(description='由 λ 区间角点导出保守概率')
    parser.add_argument('--lam-h', required=True, type=float)
    parser.add_argument('--lam-a', required=True, type=float)
    parser.add_argument('--h-interval', required=True, help='λ_H 区间，如 1.38,1.86')
    parser.add_argument('--a-interval', required=True, help='λ_A 区间，如 0.86,1.28')
    parser.add_argument('--handicap', type=int, default=None, help='竞彩主队让球线，主让1填 -1')
    parser.add_argument('--top-scores', type=int, default=3)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)

    h_lo, h_hi = _parse_interval(args.h_interval, '--h-interval')
    a_lo, a_hi = _parse_interval(args.a_interval, '--a-interval')
    model = conservative_model(args.lam_h, args.lam_a, h_lo, h_hi, a_lo, a_hi)

    point = result_probabilities(score_matrix(args.lam_h, args.lam_a))
    payload = {
        'lambda': {'h': args.lam_h, 'a': args.lam_a,
                   'h_interval': [h_lo, h_hi], 'a_interval': [a_lo, a_hi]},
        'p_model': list(point),
        'p_conservative': list(model['result']),
        'worst_corner': [CORNER_LABELS[i] for i in model['result_worst_corner']],
        'total_goals_conservative': list(model['total_goals']),
        'top_scores': [
            {'score': f'{i}-{j}', 'p_conservative': p}
            for i, j, p in conservative_top_scores(model, args.top_scores)
        ],
    }
    if args.handicap is not None:
        payload['handicap'] = {
            'line': args.handicap,
            'p_conservative': list(conservative_handicap(model, args.handicap)),
        }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    pct = lambda seq: '/'.join(f'{v * 100:.1f}%' for v in seq)  # noqa: E731
    print(f'λ_H={args.lam_h}｜λ_A={args.lam_a}｜λ区间=H[{h_lo},{h_hi}]/A[{a_lo},{a_hi}]')
    print(f'p_model_H/D/A={pct(point)}')
    print(f'保守P={pct(model["result"])}')
    print(f'最差角点（主/平/客）={"、".join(payload["worst_corner"])}')
    if args.handicap is not None:
        print(f'让球线={args.handicap}｜保守P(让胜/让平/让负)={pct(payload["handicap"]["p_conservative"])}')
    print('总球保守分布：' + '｜'.join(
        f'{n}球={p * 100:.1f}%' for n, p in enumerate(model['total_goals']) if p >= 0.005
    ))
    print('比分保守Top：' + '｜'.join(
        f'{item["score"]}={item["p_conservative"] * 100:.1f}%' for item in payload['top_scores']
    ))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
