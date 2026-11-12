#!/usr/bin/env python3
"""赛前冻结账本的打分器：校准、Log Loss/Brier、保守概率诊断、CLV、ρ 标定。

只读赛前写入的账本，不回写、不补值。历史缺概率的场不进概率指标。

用法：
    python3 scripts/score_ledger.py <日夹或仓库根>          # 打分
    python3 scripts/score_ledger.py --init <目录>            # 写空账本表头
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

PRED_COLUMNS = [
    'day', 'match_id', 'home', 'away', 'model_version',
    'lambda_h', 'lambda_a', 'h_lo', 'h_hi', 'a_lo', 'a_hi',
    'p_model_h', 'p_model_d', 'p_model_a',
    'p_cons_h', 'p_cons_d', 'p_cons_a',
    'sp_h', 'sp_d', 'sp_a',
    'closing_sp_h', 'closing_sp_d', 'closing_sp_a',
    'result',
]
TICKET_COLUMNS = [
    'day', 'ticket_name', 'match_ids', 'legs_count',
    'joint_p_independent', 'joint_p_conservative', 'rho_used',
    'stake_yuan', 'payout_yuan', 'hit',
]
OUTCOMES = ('H', 'D', 'A')
SUFFIX = {'H': 'h', 'D': 'd', 'A': 'a'}
BINS = [(i / 10, (i + 1) / 10) for i in range(10)]


def wilson_interval(hits, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = hits / n
    denominator = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((centre - spread) / denominator, (centre + spread) / denominator)


def _float(row, key):
    raw = (row.get(key) or '').strip()
    if not raw or raw.lower() in {'null', 'none', '未估', '弃权'}:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def read_csv(path, required_columns):
    if not path.exists():
        return None
    with path.open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    if rows:
        missing = [c for c in required_columns if c not in rows[0]]
        if missing:
            raise SystemExit(f'{path.name} 缺列：{missing}')
    return rows


def scored_rows(rows):
    """只保留赛前概率完整且已有赛果的场。"""
    out = []
    for row in rows:
        result = (row.get('result') or '').strip().upper()
        if result not in OUTCOMES:
            continue
        probs = [_float(row, f'p_model_{SUFFIX[o]}') for o in OUTCOMES]
        if any(p is None for p in probs):
            continue
        out.append((row, result, probs))
    return out


def log_loss_and_brier(scored):
    total_ll = total_brier = 0.0
    for _, result, probs in scored:
        index = OUTCOMES.index(result)
        p = min(max(probs[index], 1e-15), 1 - 1e-15)
        total_ll += -math.log(p)
        total_brier += sum(
            (probs[i] - float(i == index)) ** 2 for i in range(3)
        )
    n = len(scored)
    return total_ll / n, total_brier / n


def calibration_table(scored, prefix):
    """按预测概率分桶，比较桶内均值与实际命中率。"""
    buckets = {b: [] for b in BINS}
    for row, result, _ in scored:
        for outcome in OUTCOMES:
            p = _float(row, f'{prefix}_{SUFFIX[outcome]}')
            if p is None:
                continue
            hit = 1 if outcome == result else 0
            for low, high in BINS:
                if low <= p < high or (high == 1.0 and p == 1.0):
                    buckets[(low, high)].append((p, hit))
                    break
    lines = []
    for (low, high), pairs in buckets.items():
        if not pairs:
            continue
        n = len(pairs)
        mean_p = sum(p for p, _ in pairs) / n
        hits = sum(h for _, h in pairs)
        rate = hits / n
        lo, hi = wilson_interval(hits, n)
        lines.append(
            f'  [{low:.1f},{high:.1f})  n={n:<5d} 预测均值={mean_p * 100:5.1f}%  '
            f'实际命中={rate * 100:5.1f}% [{lo * 100:.1f},{hi * 100:.1f}]  '
            f'偏差={(rate - mean_p) * 100:+5.1f}pp'
        )
    return lines


def conservative_diagnostic(scored):
    """保守概率是否真的保守。

    三个量：
    - Σp_cons：worst-case 丢弃了多少概率质量，越低越保守；
    - 校准缺口 mean(命中 - p_cons)：正值=过保守（漏钱），负值=保守不足（危险）；
    - 被挡掉的正EV选项数：保守闸的直接代价。
    """
    mass = []
    gaps = []
    blocked = 0
    evaluated = 0
    for row, result, probs in scored:
        cons = [_float(row, f'p_cons_{SUFFIX[o]}') for o in OUTCOMES]
        if any(c is None for c in cons):
            continue
        mass.append(sum(cons))
        for i, outcome in enumerate(OUTCOMES):
            gaps.append((1 if outcome == result else 0) - cons[i])
            sp = _float(row, f'sp_{SUFFIX[outcome]}')
            if sp is None or sp <= 1:
                continue
            evaluated += 1
            if probs[i] * sp - 1 > 0 and cons[i] * sp - 1 <= 0:
                blocked += 1
    if not gaps:
        return ['  账本无 p_cons 列数据，无法诊断。']

    lines = [
        f'  Σp_cons 均值={sum(mass) / len(mass) * 100:.1f}%'
        f'（点估计恒为100%；差值=worst-case 丢弃的概率质量）',
        f'  校准缺口 mean(命中 - 保守P)={sum(gaps) / len(gaps) * 100:+.1f}pp'
        f'（>0 过保守，<0 保守不足）',
    ]
    if evaluated:
        lines.append(
            f'  被保守闸挡掉的正EV选项：{blocked}/{evaluated}'
            f'（{blocked / evaluated * 100:.1f}%）'
        )
    else:
        lines.append('  被保守闸挡掉的正EV选项：缺 SP 数据，无法计算')
    return lines



def clv_report(scored):
    """CLV = 实际SP / closing SP - 1；正值表示买到了比收盘更好的价。"""
    values = []
    for row, _, _ in scored:
        for outcome in OUTCOMES:
            sp = _float(row, f'sp_{SUFFIX[outcome]}')
            closing = _float(row, f'closing_sp_{SUFFIX[outcome]}')
            if sp and closing and sp > 1 and closing > 1:
                values.append(sp / closing - 1)
    if not values:
        return None
    mean = sum(values) / len(values)
    return len(values), mean


def rho_diagnostic(rows):
    """多腿票的实际命中率 vs 独立近似预测，用于标定相关性折扣 ρ。"""
    multi = []
    for row in rows:
        hit = (row.get('hit') or '').strip()
        legs = _float(row, 'legs_count')
        indep = _float(row, 'joint_p_independent')
        if hit not in {'0', '1'} or not legs or legs < 2 or indep is None:
            continue
        multi.append((int(hit), indep, _float(row, 'joint_p_conservative'),
                      _float(row, 'rho_used')))
    if not multi:
        return None
    n = len(multi)
    hits = sum(h for h, _, _, _ in multi)
    mean_indep = sum(i for _, i, _, _ in multi) / n
    cons = [c for _, _, c, _ in multi if c is not None]
    mean_cons = sum(cons) / len(cons) if cons else None
    lo, hi = wilson_interval(hits, n)
    return {
        'n': n, 'hits': hits, 'rate': hits / n, 'interval': (lo, hi),
        'mean_independent': mean_indep, 'mean_conservative': mean_cons,
    }


def write_headers(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    created = []
    for name, columns in (('pred-ledger.csv', PRED_COLUMNS),
                          ('tickets-ledger.csv', TICKET_COLUMNS)):
        path = directory / name
        if path.exists():
            print(f'跳过（已存在）：{path}')
            continue
        with path.open('w', encoding='utf-8', newline='') as handle:
            csv.writer(handle).writerow(columns)
        created.append(path)
    for path in created:
        print(f'已写表头：{path}')
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description='赛前账本打分')
    parser.add_argument('directory', help='含 pred-ledger.csv 的目录')
    parser.add_argument('--init', action='store_true', help='只写空账本表头')
    args = parser.parse_args(argv)

    directory = Path(args.directory)
    if args.init:
        return write_headers(directory)

    pred_path = directory / 'pred-ledger.csv'
    rows = read_csv(pred_path, PRED_COLUMNS)
    if rows is None:
        print(f'未找到 {pred_path}；先运行 --init 建账本。')
        return 1

    scored = scored_rows(rows)
    print(f'账本：{pred_path}')
    print(f'总行数={len(rows)}｜概率完整且已开赛={len(scored)}')
    if not scored:
        print('无可打分样本。小样本不宣称稳定盈利，也不宣称校准。')
        return 0

    ll, brier = log_loss_and_brier(scored)
    print(f'\n主指标  Log Loss={ll:.4f}（三项均匀基准={math.log(3):.4f}）  Brier={brier:.4f}'
          f'（均匀基准={2 / 3:.4f}）')

    print('\n【p_model 校准】偏差>0 = 预测偏低（保守），<0 = 预测偏高（过度自信）')
    for line in calibration_table(scored, 'p_model'):
        print(line)

    print('\n【保守P 诊断】')
    for line in conservative_diagnostic(scored):
        print(line)

    print('\n【保守P 分桶】命中率应系统性高于预测均值，否则保守不足')
    for line in calibration_table(scored, 'p_cons'):
        print(line)

    clv = clv_report(scored)
    print('\n【CLV】')
    if clv:
        print(f'  可比选项 n={clv[0]}｜平均 CLV={clv[1] * 100:+.2f}%')
    else:
        print('  缺 closing SP，无法计算')

    ticket_path = directory / 'tickets-ledger.csv'
    ticket_rows = read_csv(ticket_path, TICKET_COLUMNS)
    print('\n【ρ 相关性标定】')
    if not ticket_rows:
        print(f'  未找到 {ticket_path} 或为空；ρ 仍未标定，多腿票须显式标注。')
    else:
        rho = rho_diagnostic(ticket_rows)
        if not rho:
            print('  无 legs_count≥2 且已结算的多腿票；ρ 仍未标定。')
        else:
            lo, hi = rho['interval']
            print(f"  多腿票 n={rho['n']}｜实际命中={rho['rate'] * 100:.1f}% [{lo * 100:.1f},{hi * 100:.1f}]")
            print(f"  独立近似预测均值={rho['mean_independent'] * 100:.1f}%")
            if rho['mean_conservative'] is not None:
                print(f"  保守预测均值={rho['mean_conservative'] * 100:.1f}%")
            print('  实际命中显著低于独立近似 → 相关性被低估，应下调 ρ；'
                  '接近保守预测 → ρ 标定合理。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
