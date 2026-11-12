#!/usr/bin/env python3
"""V18 日稿伴随审计：文件存在性、赛前快照、票面逐路概率与 EV。
不联网，不证明网页内容真实，也不代替人工核验事实和预测准确率。
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import sys

MATCH = re.compile(r'(?<!\d)(\d{3})(?!\d)')
CAND = re.compile(r'【票面候选】([^\n]*)')
SCORE = re.compile(r'(?<!\d)(?:周[一二三四五六日天])?(\d{3})(?!\d)')
MONEY = Decimal('2')
REQUIRED_01A = ('【近况比分表】', '【赛程前后】', '【排除因果】', '【反剧本因果】', '【三页取证】')


def dec(value, label, errors, *, positive=True):
    try:
        d = Decimal(str(value))
        if not d.is_finite() or (positive and d <= 0):
            raise InvalidOperation
        return d
    except (InvalidOperation, TypeError, ValueError):
        errors.append(f'{label} 非有效正数: {value!r}')
        return None


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def evidence(day_dir, draft, manifest):
    errors, unverified = [], []
    text = draft.read_text(encoding='utf-8')
    match = CAND.search(text)
    if not match:
        return ['01 缺【票面候选】'], []
    line = match.group(1).split('剔=', 1)[0]
    candidates = set(MATCH.findall(line))
    if '无' in line or '候选空' in line:
        candidates = set()
    listed = manifest.get('matches', {})
    if not isinstance(listed, dict):
        return ['evidence.matches 必须为对象'], []
    if set(listed) != candidates:
        errors.append(f'证据清单场次 {sorted(listed)} 与候选 {sorted(candidates)} 不同')
    raw_root = (day_dir / '_raw').resolve()
    for num in sorted(candidates):
        sidecar = day_dir / f'01a-认真拆-{num}.md'
        if not sidecar.is_file():
            errors.append(f'{num} 缺 01a 过程稿')
        else:
            content = sidecar.read_text(encoding='utf-8')
            errors += [f'{num} 01a 缺 {marker}' for marker in REQUIRED_01A if marker not in content]
        data = listed.get(num)
        if not isinstance(data, dict):
            errors.append(f'{num} 缺证据清单项')
            continue
        for key in ('analysisJs', 'detail', 'list_spf', 'coach', 'referee', 'cat'):
            record = data.get(key)
            if not isinstance(record, dict):
                errors.append(f'{num} 缺 {key} 证据记录')
                continue
            name, sha = record.get('path'), record.get('sha256')
            if not isinstance(name, str) or not isinstance(sha, str) or not re.fullmatch(r'[a-f0-9]{64}', sha):
                errors.append(f'{num} {key} 路径或 SHA256 无效')
                continue
            file = (day_dir / name).resolve()
            if not file.is_relative_to(raw_root) or not file.is_file():
                errors.append(f'{num} {key} 非 _raw 下可读文件: {name}')
                continue
            actual = hashlib.sha256(file.read_bytes()).hexdigest()
            if actual != sha:
                errors.append(f'{num} {key} 文件哈希不符: {name}')
            if file.stat().st_size == 0:
                errors.append(f'{num} {key} 空文件: {name}')
        unverified.append(f'{num}: 文件和哈希不证明来源页面真实性、场次匹配或伤停真伪')
    return errors, unverified


def probability(value, label, errors):
    number = dec(value, label, errors, positive=False)
    if number is None or number < 0 or number > 1:
        errors.append(f'{label} 须在 0..1: {value!r}')
        return None
    return number


def check_ticket(ticket, index, candidates, watch):
    label = f'票 {index}'
    errors = []
    if not isinstance(ticket, dict):
        return [f'{label} 必须是对象']
    legs = ticket.get('legs')
    if not isinstance(legs, list) or len(legs) < 2:
        return [f'{label} 默认至少两场，legs 至少两项']
    joint = ticket.get('joint_probability')
    if joint not in ('独立近似', '保守调整'):
        errors.append(f'{label} joint_probability 须为独立近似或保守调整')
    rho = Decimal('1')
    raw_rho = ticket.get('rho')
    if joint == '保守调整' and raw_rho is None:
        errors.append(f'{label} 保守调整须写 rho（数值或“未标定”）')
    elif raw_rho is not None and str(raw_rho).strip() != '未标定':
        number = dec(raw_rho, f'{label} rho', [])
        if number is None or number <= 0 or number > 1:
            errors.append(f'{label} rho 须在 0..1 或写“未标定”: {raw_rho!r}')
        else:
            rho = number
    ids = []
    combos = [(Decimal('1'), Decimal('1'), Decimal('1'))]
    count = 1
    for pos, leg in enumerate(legs, 1):
        if not isinstance(leg, dict):
            errors.append(f'{label} 腿 {pos} 格式错误')
            continue
        mid, play, choices = leg.get('match_id'), leg.get('play'), leg.get('choices')
        if not isinstance(mid, str) or not re.fullmatch(r'\d{3}', mid):
            errors.append(f'{label} 腿 {pos} match_id 须为三位字符串')
        else:
            ids.append(mid)
            if mid not in candidates or mid in watch:
                errors.append(f'{label} 场 {mid} 非候选或为观望')
        if not isinstance(play, str) or not play.strip():
            errors.append(f'{label} 腿 {pos} 缺玩法')
        if not isinstance(choices, list) or not choices:
            errors.append(f'{label} 腿 {pos} 缺具体选项、SP 和概率')
            continue
        next_combos = []
        count *= len(choices)
        for choice in choices:
            if not isinstance(choice, dict) or not isinstance(choice.get('option'), str) or not choice['option'].strip():
                errors.append(f'{label} 腿 {pos} 选项缺名称')
                continue
            sp = dec(choice.get('sp'), f'{label} 腿 {pos} SP', errors)
            p_model = probability(choice.get('p_model'), f'{label} 腿 {pos} p_model', errors)
            p_conservative = probability(choice.get('p_conservative'), f'{label} 腿 {pos} p_conservative', errors)
            if p_conservative is not None and p_model is not None and p_conservative > p_model:
                errors.append(f'{label} 腿 {pos} 保守概率不得高于模型概率')
            if sp is not None and p_model is not None and p_conservative is not None:
                next_combos.extend((base_sp * sp, base_p * p_model, base_c * p_conservative)
                                   for base_sp, base_p, base_c in combos)
        combos = next_combos
        if '进球' in str(play):
            opts = [str(c.get('option', '')) for c in choices]
            if len(opts) >= 2:
                nums = [int(re.search(r'\d+', o).group()) for o in opts if re.search(r'\d+', o)]
                if nums and max(nums) - min(nums) + 1 != len(nums):
                    errors.append(f'{label} 进球数区间 {sorted(nums)} 不连续')
    if len(ids) != len(set(ids)):
        errors.append(f'{label} 同场不能充作跨场串')
    multiple = ticket.get('multiple', 1)
    if isinstance(multiple, bool) or not isinstance(multiple, int) or multiple < 1:
        errors.append(f'{label} multiple 须为正整数')
        return errors
    stake = MONEY * count * multiple
    declared = dec(ticket.get('stake_yuan'), f'{label} stake_yuan', errors)
    if declared is not None and declared != stake:
        errors.append(f'{label} 本金应为 {stake} 元，填写 {declared} 元')
    if len(combos) != count:
        errors.append(f'{label} 有无法计算的 SP 或概率路径')
        return errors
    if not ticket.get('odds_captured_at'):
        errors.append(f'{label} 缺赔率采集时间 odds_captured_at')
    else:
        try:
            captured = datetime.fromisoformat(str(ticket['odds_captured_at']).replace('Z', '+00:00'))
            if captured.tzinfo is None:
                raise ValueError
        except ValueError:
            errors.append(f'{label} odds_captured_at 须为带时区的 ISO 时间')
    expected_return = sum((p_model * MONEY * multiple * product
                           for product, p_model, _ in combos), Decimal('0'))
    conservative_return = sum((p_conservative * MONEY * multiple * product
                               for product, _, p_conservative in combos), Decimal('0')) * rho
    ev = expected_return / stake - 1
    conservative_ev = conservative_return / stake - 1
    if conservative_ev <= 0:
        errors.append(f'{label} 保守EV={conservative_ev:.4%}，须大于 0；模型EV={ev:.4%}')
    return errors


def ticket_audit(day_dir, draft, manifest):
    errors = []
    text = draft.read_text(encoding='utf-8')
    line = CAND.search(text)
    candidates = set(MATCH.findall(line.group(1).split('剔=', 1)[0])) if line else set()
    watch = set()
    for sec in re.split(r'\n## ', text):
        head = sec.split('\n', 1)[0]
        mid = SCORE.search(head)
        if mid and re.search(r'方向\s*=\s*观望', sec):
            watch.add(mid.group(1))
    tickets = manifest.get('tickets')
    if not isinstance(tickets, list):
        return ['ticket.tickets 必须是数组']
    if not CAND.search(text):
        errors.append('01 缺【票面候选】')
    if '【今日票面】' not in text:
        errors.append('01 缺【今日票面】')
    if not tickets:
        if '方案=空仓' not in text and not ('稳=空' in text and '博=空' in text):
            errors.append('结构化空仓与 01 票面不符')
        return errors
    ticket_block = text.split('【今日票面】', 1)[-1]
    if '方案=空仓' in ticket_block:
        errors.append('结构化非空票与 01 空仓声明矛盾')
    for ticket in tickets:
        if isinstance(ticket, dict) and ticket.get('name') in ('稳', '博'):
            name = ticket['name']
            if re.search(rf'{name}\s*=\s*空', ticket_block):
                errors.append(f'{name} 的结构化票与 01 空票矛盾')
    if '账本=过' not in text or 'EV审计=过' not in text:
        errors.append('01 非空仓缺账本=过或EV审计=过')
    names = [t.get('name') for t in tickets if isinstance(t, dict)]
    if len(names) != len(set(names)) or any(n not in ('稳', '博') for n in names):
        errors.append('默认每晚最多一张稳和一张博；票名不得重复')
    declared_joint = set(re.findall(r'联合概率\s*=\s*(独立近似|保守调整)', ticket_block))
    for i, ticket in enumerate(tickets, 1):
        errors.extend(check_ticket(ticket, i, candidates, watch))
        if not isinstance(ticket, dict):
            continue
        joint = ticket.get('joint_probability')
        if joint not in ('独立近似', '保守调整'):
            continue
        if len(declared_joint) == 1 and joint not in declared_joint:
            errors.append(f'票 {i} joint_probability={joint} 与 01【今日票面】'
                          f'联合概率={next(iter(declared_joint))} 不一致')
        if joint == '保守调整' and not re.search(r'ρ\s*=', ticket_block):
            errors.append(f'票 {i} 为保守调整，01【今日票面】须写 ρ=数值|未标定')
    return errors


def snapshot(day_dir, draft, manifest, output):
    data = load_json(manifest)
    for k in ('day', 'captured_at', 'fixtures'):
        if k not in data:
            raise ValueError(f'快照缺 {k}')
    if not isinstance(data['fixtures'], list):
        raise ValueError('fixtures 须为数组')
    draft_text = draft.read_text(encoding='utf-8')
    sections = re.split(r'\n## ', draft_text)
    seen = set()
    for item in data['fixtures']:
        if not isinstance(item, dict) or not {'match_id','kickoff_at','lean','p_model'} <= item.keys():
            raise ValueError('每场须有 match_id/kickoff_at/lean/p_model')
        mid = item['match_id']
        if not isinstance(mid, str) or not re.fullmatch(r'\d{3}', mid) or mid in seen:
            raise ValueError('match_id 重复或无效')
        seen.add(mid)
        section = next((part for part in sections
                        if SCORE.search(part.split('\n', 1)[0]) and
                        SCORE.search(part.split('\n', 1)[0]).group(1) == mid), None)
        if section is None:
            raise ValueError(f'{mid} 在赛前稿中无场次段')
        if item['lean'] not in ('主胜', '平', '客胜', '不定'):
            raise ValueError(f'{mid} lean 无效')
        if item['lean'] == '不定' and not re.search(r'方向\s*=\s*观望', section):
            raise ValueError(f'{mid} 不定须与赛前稿观望相符')
        if item['lean'] != '不定' and not re.search(r'(?:单子倾向|倾向)\s*=\s*' + re.escape(item['lean']) + r'(?![\u4e00-\u9fff])', section):
            raise ValueError(f'{mid} 倾向与赛前稿不一致')
        kickoff = datetime.fromisoformat(item['kickoff_at'].replace('Z', '+00:00'))
        captured = datetime.fromisoformat(data['captured_at'].replace('Z', '+00:00'))
        if kickoff.tzinfo is None or captured.tzinfo is None or captured >= kickoff:
            raise ValueError(f'{mid} 截止时间必须早于开赛且含时区')
        probs = item['p_model']
        if probs is not None:
            if not isinstance(probs, dict) or set(probs) != {'主胜','平','客胜'}:
                raise ValueError(f'{mid} p_model 须三项概率或 null')
            vals = [dec(probs[k], k, [], positive=False) for k in ('主胜','平','客胜')]
            if any(v is None or v < 0 or v > 1 for v in vals) or abs(sum(vals)-1) > Decimal('0.001'):
                raise ValueError(f'{mid} 概率非 0..1 或总和不为 1')
    output = Path(output)
    if output.exists():
        raise ValueError('赛前快照已存在，禁止覆盖')
    blob = draft.read_bytes()
    canonical = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    result = {'schema': 1, 'draft_sha256': hashlib.sha256(blob).hexdigest(),
              'manifest_sha256': hashlib.sha256(canonical).hexdigest(), 'manifest': data}
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=('evidence','ticket','freeze'))
    p.add_argument('draft', type=Path)
    p.add_argument('manifest', type=Path)
    p.add_argument('--output', type=Path, help='freeze 输出路径（仅新文件）')
    args = p.parse_args(argv)
    try:
        day = args.draft.resolve().parent
        if args.mode == 'freeze':
            if not args.output:
                p.error('freeze 必须传 --output')
            snapshot(day, args.draft, args.manifest, args.output)
            print('PASS: 赛前快照已写入；须在开赛前独立归档并保留校验哈希')
            return 0
        data = load_json(args.manifest)
        errors, notes = (evidence(day, args.draft, data) if args.mode == 'evidence'
                         else (ticket_audit(day, args.draft, data), []))
        for item in errors:
            print('ERROR:', item)
        for item in notes:
            print('UNVERIFIED:', item)
        print(('FAIL' if errors else 'PASS') + f': {args.mode}，错误 {len(errors)}，事实未核 {len(notes)}')
        return 1 if errors else 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print('ERROR:', exc)
        return 2


if __name__ == '__main__':
    sys.exit(main())
