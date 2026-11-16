#!/usr/bin/env python3
"""二串一组票器：枚举当日候选组合，输出「合计SP≥2.00 且联合命中概率最高」的一组。

输入 CSV（utf-8，含表头）：
  match,option,sp,cons_p[,p_model]
示例：
  苏格兰vs北马其顿,让负-2,2.36,0.408,0.557

规则（用户规则，覆盖偏好，不代表正期望）：
  1. 两腿必须来自不同场次；
  2. 合计 SP = sp1×sp2 须 ≥ 2.00（最低翻倍）；
  3. 满足翻倍的组合中，选 cons_p1 × cons_p2（联合命中）最高者。
EV/保守EV 一并输出用于账本记录，不作闸门。
"""
from __future__ import annotations

import argparse
import csv
import itertools
import sys
from pathlib import Path


def load_options(path):
    rows = []
    with open(path, newline='', encoding='utf-8-sig') as fh:
        for row in csv.DictReader(fh):
            sp = float(row['sp'])
            cons_p = float(row['cons_p'])
            if sp <= 1 or not 0 < cons_p <= 1:
                raise ValueError(f'非法行：{row}')
            p_model = float(row['p_model']) if row.get('p_model') else None
            if p_model is not None and not 0 < p_model <= 1:
                raise ValueError(f'非法 p_model：{row}')
            rows.append({'match': row['match'].strip(), 'option': row['option'].strip(),
                         'sp': sp, 'cons_p': cons_p, 'p_model': p_model})
    if len(rows) < 2:
        raise ValueError('候选少于 2 个，无法组二串一')
    return rows


def best_combo(rows, min_sp=2.0):
    combos = []
    for a, b in itertools.combinations(rows, 2):
        if a['match'] == b['match']:
            continue
        total_sp = a['sp'] * b['sp']
        if total_sp < min_sp:
            continue
        joint_cons = a['cons_p'] * b['cons_p']
        joint_model = (a['p_model'] * b['p_model']) if a['p_model'] and b['p_model'] else None
        combos.append({'legs': (a, b), 'total_sp': total_sp,
                       'joint_cons': joint_cons, 'joint_model': joint_model,
                       'cons_ev': joint_cons * total_sp - 1,
                       'ev': (joint_model * total_sp - 1) if joint_model else None})
    return sorted(combos, key=lambda c: c['joint_cons'], reverse=True)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('csv', type=Path, help='候选选项 CSV')
    p.add_argument('--min-sp', type=float, default=2.0, help='最低合计 SP，默认 2.00')
    p.add_argument('--top', type=int, default=5, help='展示前 N 组')
    args = p.parse_args(argv)

    rows = load_options(args.csv)
    combos = best_combo(rows, args.min_sp)
    if not combos:
        print(f'无可行组合：没有任何跨场组合满足合计SP≥{args.min_sp:.2f}，本日二串一=空仓')
        return 1

    for i, c in enumerate(combos[:args.top], 1):
        a, b = c['legs']
        ev_text = f"｜EV={c['ev'] * 100:+.1f}%" if c['ev'] is not None else ''
        print(f"#{i} {a['match']}·{a['option']}({a['sp']}) × {b['match']}·{b['option']}({b['sp']})")
        print(f"   合计SP={c['total_sp']:.2f}｜联合命中={c['joint_cons'] * 100:.1f}%"
              f"｜保守EV={c['cons_ev'] * 100:+.1f}%{ev_text}")
    best = combos[0]
    print(f"推荐组合=第1组｜规则=SP≥{args.min_sp:.2f}+联合命中最高（记录EV/保守EV，不作闸）")
    return 0


if __name__ == '__main__':
    sys.exit(main())
