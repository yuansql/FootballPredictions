#!/usr/bin/env python3
"""现行稿执行门禁：只核稿面一致性与本地已保存的竞彩列表，不推断比赛结果。"""
from pathlib import Path
import re

EFFECTIVE_DAY = '2026-11-06'  # 当日样本可显式 --day 回放；历史默认不回溯新硬闸
ALIASES = {'布斯巴达': '布拉格斯巴达', '尼美根': '奈梅亨', '阿尔克马': '阿尔克马尔',
           '萨迪纳摩': '萨格勒布迪纳摩', '圣吉联合': '圣吉罗斯',
           '帕梅拉斯': '帕尔梅拉斯', '里莫': '瑞模贝雷',
           '费伦茨': '费伦茨瓦罗斯', '莱克普斯纳': '波兹南莱赫',
           '波兹南': '波兹南莱赫'}


def canonical(s):
    value = re.sub(r'\s|[※⚠*（）()]', '', s)
    return ALIASES.get(value, value)


def issue(rule, severity, match, message):
    return {'rule': rule, 'severity': severity, 'match': match, 'message': message}


def _fixture_rows(raw):
    rows = {}
    for line in raw.splitlines():
        # 已保存列表格式：sid sale 周四 009 赛事 时间 主队 - 客队 SPF... 荐
        m = re.search(r'\b(周[一二三四五六日天])\s*(\d{3})\s+(.+?)\s+荐\s+', line)
        if not m:
            continue
        prefix = m.group(3).split(' 亚欧析', 1)[0]
        # 行头可能是：赛事名 + 开赛时刻 + 中场/完场 + 比分标记 + 主队 - 客队
        parts = [p for p in re.split(r'\s+', prefix) if p]
        dash = parts.index('-') if '-' in parts else len(parts)
        head = parts[1:dash] if len(parts) > 1 else parts  # 丢掉赛事名
        skip = 0
        for p in head:
            if re.fullmatch(r'\d{1,2}(:\d{2})?', p) or p in ('中场', '完场') or re.fullmatch(r'\d+-\d+', p):
                skip += 1
            else:
                break
        home = ' '.join(head[skip:]).strip() if skip < len(head) else ''
        away = ' '.join(parts[dash + 1:]).strip() if dash < len(parts) else ''
        match = (home, away) if home and away else None
        if match:
            rows[(m.group(1), m.group(2))] = (match[0], match[1])
    return rows


def lint_execution(sections, day=None, filepath=None):
    if day and day < EFFECTIVE_DAY or not filepath:
        return []
    path = Path(filepath)
    try:
        content = path.read_text(encoding='utf-8')
    except OSError:
        return [issue('lint_execution', 'ERROR', str(path), '无法读取稿件')]
    out = []
    fixture_file = path.parent / '_raw' / 'jc-list.txt'
    fixtures = _fixture_rows(fixture_file.read_text(encoding='utf-8')) if fixture_file.is_file() else {}
    if not fixtures:
        out.append(issue('lint_fixture_identity', 'WARN', '全文', '未检到可解析的 _raw/jc-list.txt；对阵 ID/主客队=未验证，不得标已核'))
    for sec in sections:
        header = sec['header']
        blob = '\n'.join(sec['lines'])
        match = re.search(r'(周[一二三四五六日天])(\d{3})\s+(.+?)\s+vs\s+(.+)', header, re.I)
        if match:
            weekday, num, home, away = match.groups()
            if (weekday, num) not in fixtures and fixtures:
                out.append(issue('lint_fixture_identity', 'WARN', header, f'列表未找到 {weekday}{num}；对阵未验证'))
            elif (weekday, num) in fixtures:
                source_home, source_away = fixtures[(weekday, num)]
                if canonical(home) != canonical(source_home) or canonical(away) != canonical(source_away):
                    out.append(issue('lint_fixture_identity', 'ERROR', header,
                        f'编号 {num} 主客队与竞彩列表不符：稿={home}/{away}，列表={source_home}/{source_away}；禁止借用别队近况'))
        if not re.search(r'(?:方向|推方向)\s*=\s*(?:观望|主不败|客不败|锁主|锁客|锁平)', blob):
            continue
        # 进行中/完赛必须在文首明确列为排除项，不能事后借此跳过进球。
        if re.search(r'排除\s*=\s*暂缓[^\n]*(?:已开赛|进行中|完赛)', blob):
            continue
        goal = re.search(r'(?:进球区间|进球)\s*=\s*([^｜\n|]+)', blob)
        if not goal or not re.search(r'\d', goal.group(1)):
            out.append(issue('lint_goals_required', 'ERROR', header,
                '赛前场进球须具体数字档/区间（可写弱置信）；不定、空槽或无数字不算交付'))
    # 比分弃权而强制列三格：不是错误，但复盘必须按两本账分开；审计状态不得省略。
    for marker, allowed in (('证据审计', '通过|未验证|失败|未触发'),
                            ('票面算术', '通过|未验证|失败|未触发'),
                            ('赛前冻结', '完成|未验证')):
        if not re.search(rf'{marker}\s*=\s*(?:{allowed})(?![\u4e00-\u9fff])', content):
            out.append(issue('lint_audit_status', 'ERROR', '文末', f'缺 {marker}={allowed}；不运行不能默认为通过'))
    candidate_line = re.search(r'【票面候选】([^\n]+)', content)
    if candidate_line and re.search(r'^\s*无\b', candidate_line.group(1)):
        reason = candidate_line.group(1).split('弃因=', 1)[-1]
        if re.search(r'未开售|翻倍|二串|凑不成|SP|赔率|本金', reason):
            out.append(issue('lint_candidate_order', 'ERROR', '文首',
                '候选空不得仅以未开售/赔率/翻倍/凑二串为弃因；先按情报判候选，再由出票闸排票'))
    candidate_head = candidate_line.group(1).strip() if candidate_line else ''
    if candidate_head.startswith('无') and not re.search(r'证据审计\s*=\s*未触发', content):
        out.append(issue('lint_audit_status', 'ERROR', '文末', '无候选时证据审计须写未触发'))
    if candidate_head and not candidate_head.startswith('无') and not re.search(r'证据审计\s*=\s*(?:通过|失败|未验证)', content):
        out.append(issue('lint_audit_status', 'ERROR', '文末', '有候选时证据审计不能写未触发'))
    if re.search(r'方案\s*=\s*空仓', content):
        if not re.search(r'票面算术\s*=\s*未触发', content):
            out.append(issue('lint_audit_status', 'ERROR', '文末', '空仓票面算术须写未触发，不得称翻倍审计通过'))
        if re.search(r'账本\s*=\s*过|翻倍\s*=\s*过', content.split('【今日票面】', 1)[-1]):
            out.append(issue('lint_audit_status', 'ERROR', '文末', '空仓不可写账本=过/翻倍=过'))
    elif re.search(r'票面算术\s*=\s*未触发', content):
        out.append(issue('lint_audit_status', 'ERROR', '文末', '非空仓票面算术不能写未触发'))
    if re.search(r'证据审计\s*=\s*通过|票面算术\s*=\s*通过', content):
        out.append(issue('lint_audit_status', 'WARN', '文末', '“通过”须由独立审计运行记录支撑；稿内声明本身不是证据'))
    return out


def lint_review(day_dir):
    """复盘补检；有 03 才执行，不能以 01 的 lint 代替。"""
    day_dir = Path(day_dir)
    draft, review = day_dir / '01-竞彩分析.md', day_dir / '03-复盘.md'
    if not review.is_file():
        return []
    if not draft.is_file():
        return [issue('lint_review_denominator', 'ERROR', '03', '缺 01，复盘分母无法核对')]
    text, recap = draft.read_text(encoding='utf-8'), review.read_text(encoding='utf-8')
    out = []
    header = re.search(r'\|\s*编号\s*\|[^\n]+', text)
    if header:
        cols = [c.strip() for c in header.group(0).strip('|').split('|')]
        if '比分' in cols and '强制' in cols:
            i_score, i_forced = cols.index('比分'), cols.index('强制')
            rows = re.findall(r'^\|\s*(?:周[一二三四五六日天])?\d{3}\s*\|[^\n]+', text, re.M)
            played = forced = 0
            for row in rows:
                cells = [c.strip() for c in row.strip('|').split('|')]
                if len(cells) > max(i_score, i_forced):
                    played += int('弃权' not in cells[i_score] and bool(re.search(r'\d+-\d+', cells[i_score])))
                    forced += int(bool(re.search(r'(?:主胜|平|客胜)(?:/\d+-\d+){3}', cells[i_forced])))
            if played != forced and re.search(r'比分(?:三格|仓|命中)?\s*\|[^\n]*\b\d+\s*/\s*\d+', recap):
                if '出手比分篮' not in recap or '强制比分' not in recap:
                    out.append(issue('lint_review_denominator', 'ERROR', '03',
                        f'比分列出手 {played} 场、强制列 {forced} 场；复盘须分别点名两本账和分母，不能混写比分三格'))
    if re.search(r'空仓成立[^\n]*主\s*KPI|主\s*KPI[^\n]*空仓成立', recap):
        out.append(issue('lint_review_denominator', 'WARN', '03', '空仓只能记执行一致，不可作为命中/盈利 KPI'))
    return out
