#!/usr/bin/env python3
"""日夹总验收：01 lint + 03 复盘；伴随审计缺失显式 UNVERIFIED。"""
import argparse
from pathlib import Path
import re
import sys

from lint_draft import run_lint
from lint_execution import lint_review
from audit_delivery import load_json, evidence, ticket_audit


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('day_dir', type=Path)
    parser.add_argument('--day', help='可选规则日期；默认按日夹路径推断，不回溯新闸')
    args = parser.parse_args(argv)
    day_dir = args.day_dir
    draft = day_dir / '01-竞彩分析.md'
    if not draft.is_file():
        print('ERROR: 缺 01-竞彩分析.md')
        return 1
    report = run_lint(str(draft), args.day)
    errors = report['errors']
    unverified = 0
    review = lint_review(day_dir)
    for item in review:
        print(f"[{item['severity']}] {item['rule']}: {item['message']}")
    errors += sum(x['severity'] == 'ERROR' for x in review)
    text = draft.read_text(encoding='utf-8')
    cand = re.search(r'【票面候选】([^\n]*)', text)
    has_candidates = bool(cand and not cand.group(1).strip().startswith('无'))
    checks = [('证据审计', 'evidence.json', evidence, has_candidates),
              ('票面算术', 'tickets.json', ticket_audit, '方案=空仓' not in text)]
    for label, name, fn, required in checks:
        if not required:
            print(f'{label}=未触发')
            continue
        path = day_dir / name
        if not path.is_file():
            unverified += 1
            print(f'{label}=未验证｜缺 {name}')
            continue
        try:
            result = fn(day_dir, draft, load_json(path))
            problems = result[0] if isinstance(result, tuple) else result
            if problems:
                errors += len(problems)
                print(f'{label}=失败｜' + '; '.join(problems[:5]))
            else:
                print(f'{label}=通过（仅文件与算术，非事实核验）')
        except (OSError, ValueError, TypeError, KeyError) as exc:
            errors += 1
            print(f'{label}=失败｜{exc}')
    frozen = day_dir / 'predictions-frozen.json'
    if frozen.is_file():
        unverified += 1
        print('赛前冻结=完成（本地文件存在，时间真实性未验证）')
    else:
        unverified += 1
        print('赛前冻结=未验证｜缺赛前快照')
    print(f'日夹验收：ERROR={errors}，UNVERIFIED={unverified}；未验证不等于通过')
    return 1 if errors or unverified else 0


if __name__ == '__main__':
    sys.exit(main())
