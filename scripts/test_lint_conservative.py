#!/usr/bin/env python3
"""lint_conservative_probability 的正反例回归。"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('lint_draft', os.path.join(ROOT, 'scripts', 'lint_draft.py'))
lint_draft = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lint_draft)

BASE = '''交卷模式=研究板
【票面候选】005｜剔=其余数据不足

## 周四005 贝蒂斯 vs 赫塔费

【统一概率】
λ_H=1.62｜λ_A=1.05｜λ区间=H[1.38,1.86]/A[0.86,1.28]｜区间依据=近6场主客拆分+xG同源不含点球+主力中卫缺｜λ校准=对手+主客+收缩
矩阵=动态独立泊松｜尾部<0.0001｜覆盖率=0.9998｜版本=v18
p_model_H/D/A=50.6%/24.8%/24.6%｜保守P=39.3%/22.2%/16.9%

【市场与EV】
选项=主胜｜实际SP=1.80｜p_be=1/SP=55.6%｜p_model=50.6%｜保守P=39.3%｜EV=p×SP-1=-8.9%｜保守EV=-29.3%
'''

NULL = BASE.replace('p_model_H/D/A=50.6%/24.8%/24.6%｜保守P=39.3%/22.2%/16.9%',
                    'p_model_H/D/A=null｜保守P=null')
TICKET = '\n【今日票面】\n预算=按注数\n博=2元｜005主胜｜单关\n账本=过｜EV审计=过｜联合概率=独立近似\n'

CASES = [
    ('基线全绿', BASE, []),
    ('手填保守P', BASE.replace('保守P=39.3%/22.2%/16.9%', '保守P=45.0%/22.0%/18.0%', 1),
     ['角点法算得']),
    ('缺λ区间', BASE.replace('｜λ区间=H[1.38,1.86]/A[0.86,1.28]', ''), ['缺 λ区间=']),
    ('λ区间格式错', BASE.replace('λ区间=H[1.38,1.86]/A[0.86,1.28]', 'λ区间=H[1.38-1.86]/A[0.86,1.28]'),
     ['须写成 H[lo,hi]/A[lo,hi]']),
    ('点估计出界', BASE.replace('λ_H=1.62', 'λ_H=2.10'), ['点估计须落在区间内']),
    ('区间上下界写反', BASE.replace('H[1.38,1.86]', 'H[1.86,1.38]'), ['上下界写反或相等']),
    ('缺区间依据', BASE.replace('｜区间依据=近6场主客拆分+xG同源不含点球+主力中卫缺', ''), ['缺 区间依据=']),
    ('保守P高于p_model', BASE.replace('保守P=39.3%/22.2%/16.9%', '保守P=55.0%/22.2%/16.9%', 1),
     ['高于 p_model']),
    ('缺保守P', BASE.replace('｜保守P=39.3%/22.2%/16.9%', '', 1), ['缺 保守P=']),
    ('保守P格式错', BASE.replace('保守P=39.3%/22.2%/16.9%', '保守P=39.3%', 1), ['须写成三个百分数']),
    ('缺λ_H', BASE.replace('λ_H=1.62｜', ''), ['缺 λ_H=']),
    ('p_model与λ不同源', BASE.replace('p_model_H/D/A=50.6%/24.8%/24.6%', 'p_model_H/D/A=70.0%/18.0%/12.0%'),
     ['须与 λ 同源']),
    ('p_model为null', NULL, []),
    ('null却给保守P', BASE.replace('p_model_H/D/A=50.6%/24.8%/24.6%', 'p_model_H/D/A=null'),
     ['不得给 保守P 数值']),
    ('EV块单值保守P不误报', BASE.replace('p_model_H/D/A=50.6%/24.8%/24.6%｜保守P=39.3%/22.2%/16.9%',
                                          'p_model_H/D/A=50.6%/24.8%/24.6%'), ['缺 保守P=']),
    ('进票且齐全', BASE + TICKET, []),
    ('进票却null', NULL + TICKET, ['已进票却缺 p_model_H/D/A']),
    ('弃因场次不算进票', NULL + '\n【今日票面】\n预算=按注数\n大博=空｜弃因=005主胜太低\n', []),
]


def run(text, day='2026-11-13'):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, f'{day}-01-竞彩分析.md')
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(text)
        sections = lint_draft.parse_sections(path)
        return lint_draft.lint_conservative_probability(sections, day, filepath=path)


def main():
    failures = 0
    for name, text, expected in CASES:
        found = run(text)
        messages = [item['message'] for item in found]
        missing = [needle for needle in expected if not any(needle in m for m in messages)]
        unexpected = [] if expected else messages
        if missing or unexpected:
            failures += 1
            print(f'✗ {name}')
            for needle in missing:
                print(f'    缺期望: {needle}')
            for message in unexpected:
                print(f'    多余: {message}')
        else:
            severities = ','.join(sorted({i["severity"] for i in found})) or '-'
            print(f'✓ {name}（{len(found)} 条：{severities}）')

    gated = run(BASE, day='2026-11-12')
    if gated:
        failures += 1
        print(f'✗ 日闸：2026-11-12 应跳过，却报 {len(gated)} 条')
    else:
        print('✓ 日闸：2026-11-12 跳过')

    print('\n' + ('全部通过' if not failures else f'{failures} 个用例失败'))
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
