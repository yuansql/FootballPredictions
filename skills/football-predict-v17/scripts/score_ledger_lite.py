#!/usr/bin/env python3
"""一行账本打分器：读 pred-ledger.csv，输出累计校准指标与二串一模拟。

账本列：date,match,lam_h,lam_a,pH,pD,pA,consH,consD,consA,direction,pick,sp_taken,ev,cons_ev,ticket,score,note
- score 形如 1-3；空 score 的行跳过计分。
- pick 支持：主胜/平/客胜/让胜±N/让平±N/让负±N；空或 无 表示该场无研究选项。
- 二串一模拟：按日聚合有 pick 的行，执行「合计SP≥2.00 且联合保守命中最高」规则，结算 2 元票。

仅作复盘诊断，n<30 时不输出任何规则调整建议。
"""
from __future__ import annotations

import argparse
import csv
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from probability_model import brier_score, log_loss  # noqa: E402

HANDICAP_RESULT = {'让胜': 0, '让平': 1, '让负': 2}


def outcome_index(score):
    home, away = (int(x) for x in score.strip().split('-'))
    return 0 if home > away else 1 if home == away else 2


def pick_won(pick, score):
    home, away = (int(x) for x in score.strip().split('-'))
    if pick in ('主胜', '平', '客胜'):
        return outcome_index(score) == {'主胜': 0, '平': 1, '客胜': 2}[pick]
    if pick.startswith('让'):
        side = pick[:2]
        line = int(pick[2:])
        adjusted = home + line - away
        idx = 0 if adjusted > 0 else 1 if adjusted == 0 else 2
        return idx == HANDICAP_RESULT[side]
    raise ValueError(f'无法解析 pick={pick!r}')


def load(path):
    with open(path, newline='', encoding='utf-8-sig') as fh:
        rows = list(csv.DictReader(fh))
    scored = [r for r in rows if r.get('score', '').strip()]
    return rows, scored


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('ledger', type=Path)
    args = p.parse_args(argv)
    rows, scored = load(args.ledger)
    if not scored:
        print('账本中没有已填 score 的行')
        return 1

    briers, losses, hits = [], [], 0
    for r in scored:
        probs = (float(r['pH']), float(r['pD']), float(r['pA']))
        idx = outcome_index(r['score'])
        briers.append(brier_score(probs, idx))
        losses.append(log_loss(probs, idx))
        if max(range(3), key=lambda i: probs[i]) == idx:
            hits += 1
    n = len(scored)
    print(f'已记分场次={n}｜单选命中={hits}/{n}（{hits / n * 100:.0f}%）')
    print(f'平均 Brier={sum(briers) / n:.3f}（均匀基线 0.667）｜平均 LogLoss={sum(losses) / n:.3f}（基线 1.099）')

    # 二串一模拟：按日聚合有 pick 的研究选项
    by_date = {}
    for r in scored:
        pick = (r.get('pick') or '').strip()
        sp = (r.get('sp_taken') or '').strip()
        cons_ev = (r.get('cons_ev') or '').strip()
        if not pick or not sp or not cons_ev:
            continue
        sp = float(sp)
        cons_p = (float(cons_ev) + 1) / sp
        by_date.setdefault(r['date'], []).append({**r, '_sp': sp, '_cons_p': cons_p})

    played = won = 0
    staked = returned = 0.0
    for date, opts in sorted(by_date.items()):
        best = None
        for a, b in itertools.combinations(opts, 2):
            if a['match'] == b['match'] or a['_sp'] * b['_sp'] < 2.0:
                continue
            joint = a['_cons_p'] * b['_cons_p']
            if best is None or joint > best[0]:
                best = (joint, a, b)
        if best is None:
            print(f'{date} 二串一模拟=无可行组合')
            continue
        _, a, b = best
        ok = pick_won(a['pick'], a['score']) and pick_won(b['pick'], b['score'])
        played += 1
        won += ok
        staked += 2
        returned += a['_sp'] * b['_sp'] * 2 if ok else 0
        mark = '中' if ok else '失'
        print(f"{date} 二串一模拟={a['match']}·{a['pick']} × {b['match']}·{b['pick']}"
              f"｜SP={a['_sp'] * b['_sp']:.2f}｜{mark}")
    if played:
        print(f'二串一模拟累计={won}/{played}｜本金={staked:.0f} 返还={returned:.2f} '
              f'｜ROI={(returned - staked) / staked * 100:+.1f}%（n 太小，仅供参考）')
    if n < 30:
        print(f'提示：n={n}<30，不输出任何规则调整建议；攒够样本再谈校准结论。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
