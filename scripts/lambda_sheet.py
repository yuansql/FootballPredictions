#!/usr/bin/env python3
"""λ 工作表计算器：联赛基准 × 攻防强度 × 修正项 → λ 与区间。

口径见 references/lambda工作表.md。本脚本只做算术与校验，不替你做判断；
攻防强度与修正项必须由输入方给出证据。
"""
from __future__ import annotations

import argparse


def _positive(name, value, lo=0.0, hi=None):
    value = float(value)
    if not value > lo:
        raise ValueError(f'{name} 须大于 {lo}，得到 {value}')
    if hi is not None and not value <= hi:
        raise ValueError(f'{name} 须在 ({lo},{hi}]，得到 {value}')
    return value


def uncertainty(n, lineup_unknown, friendly):
    u = 0.15
    if n < 8:
        u += 0.05
    if lineup_unknown:
        u += 0.05
    if friendly:
        u += 0.05
    return min(u, 0.35)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--league-home', required=True, type=float, help='联赛主场场均进球')
    p.add_argument('--league-away', required=True, type=float, help='联赛客场场均进球')
    p.add_argument('--att-h', required=True, type=float, help='主队主场攻击强度（已收缩）')
    p.add_argument('--def-h', required=True, type=float, help='主队主场防守强度（已收缩，越小越好）')
    p.add_argument('--att-a', required=True, type=float, help='客队客场攻击强度（已收缩）')
    p.add_argument('--def-a', required=True, type=float, help='客队客场防守强度（已收缩）')
    p.add_argument('--adj-h', type=float, default=1.0, help='主队修正项连乘积，0.70~1.30')
    p.add_argument('--adj-a', type=float, default=1.0, help='客队修正项连乘积，0.70~1.30')
    p.add_argument('--n-h', type=float, default=10, help='主队口径样本场次')
    p.add_argument('--n-a', type=float, default=10, help='客队口径样本场次')
    p.add_argument('--lineup-unknown', action='store_true', help='关键阵容/首发未确认')
    p.add_argument('--friendly', action='store_true', help='友谊赛或大幅轮换预期')
    args = p.parse_args(argv)

    lg_h = _positive('--league-home', args.league_home, 0.2, 3.0)
    lg_a = _positive('--league-away', args.league_away, 0.2, 3.0)
    att_h = _positive('--att-h', args.att_h, 0.2, 3.0)
    def_h = _positive('--def-h', args.def_h, 0.2, 3.0)
    att_a = _positive('--att-a', args.att_a, 0.2, 3.0)
    def_a = _positive('--def-a', args.def_a, 0.2, 3.0)
    adj_h = _positive('--adj-h', args.adj_h, 0.69, 1.31)
    adj_a = _positive('--adj-a', args.adj_a, 0.69, 1.31)

    lam_h = lg_h * att_h * def_a * adj_h
    lam_a = lg_a * att_a * def_h * adj_a
    u_h = uncertainty(args.n_h, args.lineup_unknown, args.friendly)
    u_a = uncertainty(args.n_a, args.lineup_unknown, args.friendly)
    h_lo, h_hi = max(0.05, lam_h * (1 - u_h)), lam_h * (1 + u_h)
    a_lo, a_hi = max(0.05, lam_a * (1 - u_a)), lam_a * (1 + u_a)

    print(f'λ_H={lam_h:.2f}（{lg_h}×{att_h}×{def_a}×{adj_h}）｜λ_A={lam_a:.2f}（{lg_a}×{att_a}×{def_h}×{adj_a}）')
    print(f'u_H={u_h:.2f}｜u_A={u_a:.2f}')
    print(f'λ区间=H[{h_lo:.2f},{h_hi:.2f}]/A[{a_lo:.2f},{a_hi:.2f}]')
    print('下一步：')
    print(f'python3 scripts/conservative_probability.py --lam-h {lam_h:.2f} --lam-a {lam_a:.2f} '
          f'--h-interval {h_lo:.2f},{h_hi:.2f} --a-interval {a_lo:.2f},{a_hi:.2f}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
