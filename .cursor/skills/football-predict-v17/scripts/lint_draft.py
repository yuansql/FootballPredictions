#!/usr/bin/env python3
"""
lint_draft.py — V17.4.40 日闸 lint 工具

功能：
1. lint_low_structure_weld — 扫描 draw_priority 场是否焊死倾向
2. lint_02_atom_text — 检查 02 对外句面是否含「防平」硬焊措辞
3. lint_02_must_direction — 验证每场方向原子必给（4.22.3）
4. lint_lean_pack — 验证倾向 ∈ 允许集（4.22.4）
5. lint_exclude_three_step — 验证 排除|剩余|二次 固定行（4.27）
6. lint_exclude_intel_gate — 排除三件套：排胜负边须硬情报或盘口质疑（4.31）
7. lint_seasoning_pack — 佐料整包：可介入须见初盘+水位（4.32）
8. lint_euro_deep_away — 欧战深盘客：欧战场锁客须见闸行（4.33）
9. lint_dual_debut_lock — 双新军锁主：双新军叙事+锁主须见闸行（4.33）
10. lint_summary_table — 全场汇总表：编号/排除/推方向/单子倾向/推比分/推进球（4.34）
11. lint_handicap_only_channel — 只开让球：未开售胜平负时映射禁写单买主胜等（4.36）
12. lint_cold_upset_banner — 冷门预防统一亮牌：场场【冷门预防】触发=是|否（4.37）
13. lint_hc_spf_single — 文末【让球稳健推荐】无|≤3（4.38；兼容旧块名）
14. lint_deep_lock_receipt — 深让+锁*须【深让可锁】+初盘/水位（4.40）

用法：
    python3 lint_draft.py <草稿文件.md> [--day YYYY-MM-DD]
    python3 lint_draft.py /path/to/01-竞彩分析.md --day 2026-09-07
    python3 lint_draft.py --self-check

解析：标题含 vs/VS，或 周[一二三四五六日]001。0 场 → ERROR（禁止假绿）。

日闸常量：
    STRUCTURE_GATE_DAY = "2026-09-07"
    DIR_MUST_DAY = "2026-09-02"
    LEAN_DAY = "2026-09-04"
    EXCLUDE_DAY = "2026-09-14"
    EXCLUDE_INTEL_DAY = "2026-09-17"
    SEASONING_DAY = "2026-09-17"
    EURO_DEEP_AWAY_DAY = "2026-09-18"
    DUAL_DEBUT_DAY = "2026-09-18"
    SUMMARY_TABLE_DAY = "2026-09-18"
    HC_ONLY_DAY = "2026-09-18"
    COLD_UPSET_DAY = "2026-09-20"
    HC_SPF_SINGLE_DAY = "2026-09-20"
    DEEP_LOCK_DAY = "2026-09-22"
"""

import sys
import re
import argparse
from datetime import datetime

# === 日闸常量 ===
STRUCTURE_GATE_DAY = "2026-09-07"
DIR_MUST_DAY = "2026-09-02"
LEAN_DAY = "2026-09-04"
ICS_MIN_DAY = "2026-09-07"   # ICS≥70 或 CAUTION 从这天起检查
RED_FLAG_DAY = "2026-09-07"  # 红旗清单从这天起检查
EXCLUDE_DAY = "2026-09-14"   # 排除|剩余|二次固定行
EXCLUDE_INTEL_DAY = "2026-09-17"  # 排除三件套：硬情报/盘口质疑
SEASONING_DAY = "2026-09-17"  # 佐料整包：初盘为锚
EURO_DEEP_AWAY_DAY = "2026-09-18"  # 欧战深盘客闸 soft#8
DUAL_DEBUT_DAY = "2026-09-18"  # 双新军锁主闸 soft#9
SUMMARY_TABLE_DAY = "2026-09-18"  # 全场汇总表（排除/推方向/单子倾向/比分/进球）
HC_ONLY_DAY = "2026-09-18"  # 只开让球分通道（胜平负未开售）
COLD_UPSET_DAY = "2026-09-20"  # 冷门预防统一亮牌
HC_SPF_SINGLE_DAY = "2026-09-20"  # 让球稳健可荐文末块
DEEP_LOCK_DAY = "2026-09-22"  # 深让+锁*须【深让可锁】收据
FORM_GATE_DAY = "2026-09-16" # 状态评分硬闸从这天起检查
BOTH_SCORE_DAY = "2026-09-16" # BOTH_SCORE 比分补偿从这天起检查
STATE_CRUSH_DAY = "2026-09-16" # 状态碾压冷门预警从这天起检查
MARKET_DIV_DAY = "2026-09-16"  # 跨市场背离预警从这天起检查


# 排除三件套：硬情报 / 盘口质疑 / 软词黑名单
EXCLUDE_HARD_RE = re.compile(
    r'伤停|轮换|状态|战意|连败|克制|板凳|阵容|留力|分心|高原|深度|保级|争冠|残阵|停赛|主力缺|零封|火力'
)
EXCLUDE_MARKET_RE = re.compile(r'背离|撤热|异动|假热|亚盘|水位|降赔|升赔|初盘|终盘')
EXCLUDE_SOFT_ONLY_RE = re.compile(
    r'主场优势|主场有优势|经验|名气|抵消|纸面实力|纸面强|传统强队'
)


# === 导入 structure_gate ===
import importlib.util
import os

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("structure_gate", os.path.join(_SCRIPT_DIR, "structure_gate.py"))
structure_gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(structure_gate)

compute_structure_tag = structure_gate.compute_structure_tag
get_enforced_direction = structure_gate.get_enforced_direction
parse_sp_line = structure_gate.parse_sp_line


MATCH_CODE_RE = re.compile(r'周[一二三四五六日]\d{3}')
VS_SPLIT_RE = re.compile(r'(?i)\bvs\b')
_SKIP_HEADERS = ('复盘', '附录', '总体', '模板', '今晚研究', '钉槽', '目录', '精选场次')


def is_match_header(header: str) -> bool:
    """比赛段：vs/VS，或周一～周日+三位编号。"""
    h = header.strip()
    if any(k in h for k in _SKIP_HEADERS):
        return False
    return 'vs' in h.lower() or bool(MATCH_CODE_RE.search(h))


def parse_sections(filepath: str) -> list[dict]:
    """解析 markdown 草稿文件，返回比赛段列表。"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    sections = []
    parts = re.split(r'\n## ', content)
    for part in parts:
        lines = part.strip().split('\n')
        if not lines:
            continue
        header = lines[0].strip().lstrip('#').strip()
        if not is_match_header(header):
            continue
        sections.append({
            'header': header,
            'lines': lines,
            'raw': part,
        })
    return sections


def lint_low_structure_weld(sections: list[dict], day: str | None = None) -> list[dict]:
    """
    低结构焊死倾向检测。
    draw_priority 场若写了「主胜」「客胜」「锁平」→ warn。
    """
    if day and day < STRUCTURE_GATE_DAY:
        return []

    warnings = []
    for sec in sections:
        lines = sec['lines']
        header = sec['header']

        # 提取 SP
        sp = None
        for line in lines:
            sp = parse_sp_line(line)
            if sp:
                break
        if not sp:
            continue

        tag = compute_structure_tag(sp[0], sp[1], sp[2])
        if tag != "draw_priority":
            continue

        # 检查是否焊死倾向
        for line in lines:
            if '方向｜倾向｜比分' in line or '方向｜' in line:
                # draw_priority 场禁止倾向主胜/客胜/锁平
                if re.search(r'倾向\s*主胜|倾向\s*客胜|锁\s*平|锁主|锁客', line):
                    warnings.append({
                        'rule': 'lint_low_structure_weld',
                        'severity': 'WARN',
                        'match': header,
                        'sp': sp,
                        'line': line.strip(),
                        'message': f"draw_priority 场焊死倾向: {line.strip()[:80]}"
                    })
                break
    return warnings


def lint_02_atom_text(sections: list[dict], day: str | None = None) -> list[dict]:
    """
    检查 02 对外句面是否含「防平」硬焊措辞。
    仅检测真正的硬焊：把防平与锁单写在一起，如「主胜（防平）」「锁主防平」。
    正常的「倾向主胜｜1-1 防」不算硬焊。
    """
    if day and day < STRUCTURE_GATE_DAY:
        return []

    warnings = []
    # 硬焊措辞：锁单与防平混写、或把防平当方向的一部分
    hard_weld_patterns = [
        r'主胜\s*[(（].*防平',      # 主胜（防平）
        r'客胜\s*[(（].*防平',      # 客胜（防平）
        r'锁[主客平].*防平',         # 锁主防平、锁客防平
        r'防平.*锁[主客平]',         # 防平锁主
        r'主胜防平|客胜防平|锁平防主|锁平防客',  # 无括号直接连写
    ]

    for sec in sections:
        lines = sec['lines']
        header = sec['header']

        for line in lines:
            # 跳过 01 内部格式行（方向= / 单子倾向= / 方向三步），只检查 02 对外句面
            if '方向=' in line or '单子倾向=' in line or '【方向三步】' in line:
                continue
            for pat in hard_weld_patterns:
                if re.search(pat, line):
                    warnings.append({
                        'rule': 'lint_02_atom_text',
                        'severity': 'WARN',
                        'match': header,
                        'line': line.strip(),
                        'message': f"02 句面硬焊措辞: {line.strip()[:80]}"
                    })
                    break
    return warnings


def lint_02_must_direction(sections: list[dict], day: str | None = None) -> list[dict]:
    """
    4.22.3 方向必须给。检查每场是否有方向原子。
    """
    if day and day < DIR_MUST_DAY:
        return []

    warnings = []
    valid_atoms = ['锁主', '锁客', '锁平', '主不败', '客不败', '主胜', '客胜', '平局']

    for sec in sections:
        lines = sec['lines']
        header = sec['header']

        has_direction = False
        for line in lines:
            if '方向｜倾向｜比分' in line or '方向｜' in line or '方向=' in line:
                for atom in valid_atoms:
                    if atom in line:
                        has_direction = True
                        break
                break

        if not has_direction:
            warnings.append({
                'rule': 'lint_02_must_direction',
                'severity': 'ERROR',
                'match': header,
                'message': "方向原子缺失（禁止空槽/胶着）"
            })
    return warnings


def lint_lean_pack(sections: list[dict], day: str | None = None) -> list[dict]:
    """
    4.22.4 倾向必须 ∈ 允许集。
    单子倾向只能是：主胜 / 客胜 / 平 / 不定。
    """
    if day and day < LEAN_DAY:
        return []

    # 方向 → 允许倾向集合（含不定）
    allowed_leans = {
        '锁主':  {'主胜', '不定'},
        '锁客':  {'客胜', '不定'},
        '锁平':  {'平', '不定'},
        '主不败': {'主胜', '平', '不定'},
        '客不败': {'客胜', '平', '不定'},
        '主胜':  {'主胜', '不定'},
        '客胜':  {'客胜', '不定'},
        '平局':  {'平', '不定'},
    }

    valid_lean_tokens = {'主胜', '客胜', '平', '不定'}

    warnings = []
    for sec in sections:
        lines = sec['lines']
        header = sec['header']

        direction = None
        lean = None
        for line in lines:
            if '方向｜倾向｜比分' in line or '方向｜' in line or '方向=' in line:
                if '主不败' in line:
                    direction = '主不败'
                elif '客不败' in line:
                    direction = '客不败'
                elif '锁主' in line:
                    direction = '锁主'
                elif '锁客' in line:
                    direction = '锁客'
                elif '锁平' in line:
                    direction = '锁平'
                elif '主胜' in line and '倾向' not in line and '单子倾向' not in line:
                    direction = '主胜'
                elif '客胜' in line and '倾向' not in line and '单子倾向' not in line:
                    direction = '客胜'
                elif '平局' in line:
                    direction = '平局'

                # 提取倾向（优先 02 格式，回退 01 格式）
                # 02 格式: 倾向 主胜｜...（倾向前面不是"单子"）
                m = re.search(r'(?<!单子)倾向\s*([^｜\|]+)', line)
                if not m:
                    # 01 格式: 单子倾向=主胜｜...
                    m = re.search(r'单子倾向\s*=\s*([^｜\|]+)', line)
                if m:
                    lean = m.group(1).strip()
                    # 去掉括号注释如 "主胜（防平）"
                    lean = re.split(r'[（(]', lean)[0].strip()
                break

        if not direction:
            continue
        if not lean:
            # 方向给了但倾向缺失：锁* 场可省略（等同所锁），但主不败/客不败必须写倾向或不定
            if direction in ('主不败', '客不败'):
                warnings.append({
                    'rule': 'lint_lean_pack',
                    'severity': 'WARN',
                    'match': header,
                    'message': f"{direction} 场倾向缺失（应写 主胜/客胜/平/不定）"
                })
            continue

        # 倾向必须是合法 token
        if lean not in valid_lean_tokens:
            warnings.append({
                'rule': 'lint_lean_pack',
                'severity': 'ERROR',
                'match': header,
                'message': f"倾向非法 '{lean}'（只能是 主胜/客胜/平/不定）"
            })
            continue

        # 倾向必须在方向允许集内
        allowed = allowed_leans.get(direction, set())
        if lean not in allowed:
            warnings.append({
                'rule': 'lint_lean_pack',
                'severity': 'ERROR',
                'match': header,
                'message': f"{direction} 场倾向 '{lean}' 超出允许集（允许: {allowed}）"
            })

    return warnings


def _parse_remaining_set(rem_raw: str) -> set[str]:
    """Parse 剩余={主胜,平} or {主,平}/{客,平}/{主,客}."""
    s = rem_raw.replace('，', ',').strip()
    if re.search(r'主胜\s*,\s*平|平\s*,\s*主胜', s) or re.search(r'^\s*主\s*,\s*平\s*$', s) or re.search(r'^\s*平\s*,\s*主\s*$', s):
        return {'主胜', '平'}
    if re.search(r'客胜\s*,\s*平|平\s*,\s*客胜', s) or re.search(r'^\s*客\s*,\s*平\s*$', s) or re.search(r'^\s*平\s*,\s*客\s*$', s):
        return {'客胜', '平'}
    if re.search(r'主胜\s*,\s*客胜|客胜\s*,\s*主胜', s) or re.search(r'^\s*主\s*,\s*客\s*$', s) or re.search(r'^\s*客\s*,\s*主\s*$', s):
        return {'主胜', '客胜'}
    tokens = set()
    for tok in ('主胜', '客胜', '平'):
        if tok in s:
            tokens.add(tok)
    return tokens


def lint_exclude_three_step(sections: list[dict], day: str | None = None) -> list[dict]:
    """
    V17.4.27：01 每场须有 排除=｜剩余=｜二次=（二次须含 倾斜…→ 或 分不清→ 分叉）。
    剩{主胜,客胜} 禁止二次写主不败/客不败。
    """
    if day and day < EXCLUDE_DAY:
        return []

    warnings = []
    valid_exclude = {'主胜', '平', '客胜'}
    valid_secondary = {'锁主', '锁平', '锁客', '主不败', '客不败'}

    for sec in sections:
        header = sec['header']
        blob = '\n'.join(sec['lines'])

        if '方向=' not in blob and '【方向三步】' not in blob and '排除=' not in blob:
            continue

        m_ex = re.search(r'排除\s*=\s*(主胜|平|客胜)', blob)
        m_rem = re.search(r'剩余\s*=\s*\{([^}]+)\}', blob)
        # 二次=… → 锁主|…  （允许中间夹 倾斜/分不清/深让降维）
        m_sec = re.search(
            r'二次\s*=\s*([^\n]*?)(→|->)\s*(锁主|锁平|锁客|主不败|客不败)',
            blob,
        )
        # 兼容旧稿：二次=锁主（无箭头）
        m_sec_legacy = re.search(r'二次\s*=\s*(锁主|锁平|锁客|主不败|客不败)\b', blob)

        if not m_ex:
            warnings.append({
                'rule': 'lint_exclude_three_step',
                'severity': 'ERROR',
                'match': header,
                'message': '缺少 排除=<主胜|平|客胜>（V17.4.27 固定行）',
            })
            continue

        exclude = m_ex.group(1)
        rem_tokens: set[str] = set()
        if not m_rem:
            warnings.append({
                'rule': 'lint_exclude_three_step',
                'severity': 'ERROR',
                'match': header,
                'message': '缺少 剩余={…}（V17.4.27 固定行）',
            })
        else:
            rem_tokens = _parse_remaining_set(m_rem.group(1))

        if m_sec:
            secondary = m_sec.group(3)
            fork = m_sec.group(1) or ''
            if ('倾斜' not in fork) and ('分不清' not in fork) and ('深让' not in fork):
                warnings.append({
                    'rule': 'lint_exclude_three_step',
                    'severity': 'WARN',
                    'match': header,
                    'message': '二次= 箭头前须含「倾斜…」或「分不清」（或深让降维说明）',
                })
        elif m_sec_legacy:
            secondary = m_sec_legacy.group(1)
            warnings.append({
                'rule': 'lint_exclude_three_step',
                'severity': 'WARN',
                'match': header,
                'message': '二次= 缺分叉（应为 倾斜…→锁* 或 分不清→不败｜单子腿=）',
            })
        else:
            warnings.append({
                'rule': 'lint_exclude_three_step',
                'severity': 'ERROR',
                'match': header,
                'message': '缺少 二次=倾斜…→锁* 或 分不清→不败（V17.4.27）',
            })
            continue

        if secondary not in valid_secondary:
            warnings.append({
                'rule': 'lint_exclude_three_step',
                'severity': 'ERROR',
                'match': header,
                'message': f"二次非法 '{secondary}'",
            })
            continue

        if rem_tokens and len(rem_tokens) == 2:
            expected = valid_exclude - {exclude}
            if rem_tokens != expected:
                warnings.append({
                    'rule': 'lint_exclude_three_step',
                    'severity': 'WARN',
                    'match': header,
                    'message': f"剩余 {rem_tokens} 与排除={exclude} 不一致（期望 {expected}）",
                })

        if rem_tokens == {'主胜', '客胜'} and secondary in ('主不败', '客不败'):
            warnings.append({
                'rule': 'lint_exclude_three_step',
                'severity': 'ERROR',
                'match': header,
                'message': '剩余={主胜,客胜} 禁止二次写主不败/客不败（须锁主|锁客）',
            })

        if secondary == '主不败' and rem_tokens and rem_tokens != {'主胜', '平'}:
            warnings.append({
                'rule': 'lint_exclude_three_step',
                'severity': 'WARN',
                'match': header,
                'message': f"二次→主不败 但剩余={rem_tokens}（期望 {{主胜,平}}）",
            })
        if secondary == '客不败' and rem_tokens and rem_tokens != {'客胜', '平'}:
            warnings.append({
                'rule': 'lint_exclude_three_step',
                'severity': 'WARN',
                'match': header,
                'message': f"二次→客不败 但剩余={rem_tokens}（期望 {{客胜,平}}）",
            })

    return warnings


def lint_exclude_intel_gate(sections: list[dict], day: str | None = None) -> list[dict]:
    """
    V17.4.31 排除三件套：排除=主胜/客胜 时，理由须含硬情报词，或质疑=含盘口词。
    禁止仅软词（主场优势/经验/名气/抵消…）排胜负边。排除=平 不强制硬词。
    """
    if day and day < EXCLUDE_INTEL_DAY:
        return []

    warnings = []
    for sec in sections:
        header = sec['header']
        blob = '\n'.join(sec['lines'])
        if '排除=' not in blob and '排除 =' not in blob:
            continue

        m = re.search(
            r'排除\s*=\s*(主胜|平|客胜)\s*｜\s*理由\s*=\s*([^｜\n]+)(?:\s*｜\s*质疑\s*=\s*([^｜\n]+))?',
            blob,
        )
        if not m:
            # 兼容无「质疑=」旧行：排除=X｜理由=Y
            m = re.search(r'排除\s*=\s*(主胜|平|客胜)\s*｜\s*理由\s*=\s*([^｜\n]+)', blob)
        if not m:
            continue

        exclude = m.group(1)
        reason = m.group(2).strip()
        challenge = (m.group(3).strip() if m.lastindex >= 3 and m.group(3) else '')

        if exclude == '平':
            if not reason or reason in ('·', '…', '-'):
                warnings.append({
                    'rule': 'lint_exclude_intel_gate',
                    'severity': 'ERROR',
                    'match': header,
                    'message': '排除=平 仍须写非空理由（V17.4.31）',
                })
            continue

        # 排主胜/客胜
        has_hard = bool(EXCLUDE_HARD_RE.search(reason))
        has_market = bool(EXCLUDE_MARKET_RE.search(reason) or EXCLUDE_MARKET_RE.search(challenge))
        # 质疑=无 不算市场质疑
        if challenge in ('无', '·', '…', '-', ''):
            challenge_ok = False
        else:
            challenge_ok = bool(EXCLUDE_MARKET_RE.search(challenge)) or has_market

        soft_hit = bool(EXCLUDE_SOFT_ONLY_RE.search(reason))
        if soft_hit and not has_hard and not challenge_ok:
            warnings.append({
                'rule': 'lint_exclude_intel_gate',
                'severity': 'ERROR',
                'match': header,
                'message': (
                    f'排除={exclude} 理由「{reason}」像软词排胜负边；'
                    f'须硬情报（伤停/轮换/状态/战意/连败/克制/板凳…）或质疑=盘口词 (V17.4.31)'
                ),
            })
            continue

        if not has_hard and not challenge_ok:
            warnings.append({
                'rule': 'lint_exclude_intel_gate',
                'severity': 'ERROR',
                'match': header,
                'message': (
                    f'排除={exclude} 缺硬情报词且无盘口质疑；'
                    f'SP 不得单独决定排除 (V17.4.31 三件套)'
                ),
            })

    return warnings


def lint_seasoning_pack(sections: list[dict], day: str | None = None) -> list[dict]:
    """
    V17.4.32 佐料整包：【出票】可介入/试探 时，须同屏有初盘锚 + 水位路径标记。
    观望场不强制（仍鼓励写）。
    """
    if day and day < SEASONING_DAY:
        return []

    warnings = []
    ticket_intervene = re.compile(r'【出票】[^\n]*(可介入|可试探|试探)')
    has_open = re.compile(r'初盘\s*=')
    has_water = re.compile(r'水位路径\s*=|水位\s*=')

    for sec in sections:
        header = sec['header']
        blob = '\n'.join(sec['lines'])
        if not ticket_intervene.search(blob):
            continue
        if '不荐' in blob and re.search(r'【出票】[^\n]*不荐', blob):
            # 同行既可介入又不荐极少；若明确不荐则跳过
            if re.search(r'【出票】\s*不荐', blob) and not re.search(r'【出票】[^\n]*可介入', blob):
                continue
        missing = []
        if not has_open.search(blob):
            missing.append('初盘=')
        if not has_water.search(blob):
            missing.append('水位路径=')
        if missing:
            warnings.append({
                'rule': 'lint_seasoning_pack',
                'severity': 'ERROR',
                'match': header,
                'message': (
                    f'出票可介入但缺佐料整包标记 {",".join(missing)}；'
                    f'初盘为锚、水位看路径，禁只报即时SP (V17.4.32)'
                ),
            })

    return warnings


def lint_deep_lock_receipt(sections: list[dict], day: str | None = None) -> list[dict]:
    """
    V17.4.40：触深让/深热警示且方向=锁* 时，须【深让可锁】且含初盘= + 水位=/水位路径=。
    走不败/降维不拦。检测：明确深让词，或让球≤-1.5/≥+1.5，或热侧 SP≤1.35。
    """
    if day and day < DEEP_LOCK_DAY:
        return []

    lock_re = re.compile(r'方向\s*=\s*锁(主|客)|二次\s*=[^\n]*→\s*锁(主|客)')
    deep_word_re = re.compile(r'深让|深热|触深让|【深让')
    deep_ah_re = re.compile(
        r'(?:让球|亚盘|盘口|主让|客让)\s*[=:：]?\s*'
        r'(?:主[让\-]?)?-?(?:1\.5|2(?:\.0)?|2\.5|3)|'
        r'(?:客[让\+]?)?\+?(?:1\.5|2(?:\.0)?|2\.5|3)'
    )
    banner_re = re.compile(r'【深让可锁】[^\n]*')
    has_open = re.compile(r'初盘\s*=')
    has_water = re.compile(r'水位路径\s*=|水位\s*=')
    sp_home_re = re.compile(r'(?:主胜\s*SP|SP[_ ]?H|主\s*SP)\s*[=:：]?\s*(\d+\.?\d*)', re.I)
    sp_away_re = re.compile(r'(?:客胜\s*SP|SP[_ ]?A|客\s*SP)\s*[=:：]?\s*(\d+\.?\d*)', re.I)

    warnings = []
    for sec in sections:
        header = sec['header']
        blob = '\n'.join(sec['lines'])
        lm = lock_re.search(blob)
        if not lm:
            continue
        lock_side = lm.group(1) or lm.group(2)  # 主|客
        deep = bool(deep_word_re.search(blob) or deep_ah_re.search(blob))
        if not deep:
            # 热侧 SP≤1.35 也算深热警示
            if lock_side == '主':
                sm = sp_home_re.search(blob)
                if sm and float(sm.group(1)) <= 1.35:
                    deep = True
            else:
                sm = sp_away_re.search(blob)
                if sm and float(sm.group(1)) <= 1.35:
                    deep = True
        if not deep:
            continue
        bm = banner_re.search(blob)
        if not bm:
            warnings.append({
                'rule': 'lint_deep_lock_receipt',
                'severity': 'ERROR',
                'match': header,
                'message': (
                    '深让/深热警示下锁* 须写【深让可锁】触发=是｜初盘=…｜水位=… '
                    '(V17.4.40；禁空喊锁*)'
                ),
            })
            continue
        line = bm.group(0)
        missing = []
        if not has_open.search(line) and not has_open.search(blob):
            missing.append('初盘=')
        if not has_water.search(line) and not has_water.search(blob):
            missing.append('水位=')
        if missing:
            warnings.append({
                'rule': 'lint_deep_lock_receipt',
                'severity': 'ERROR',
                'match': header,
                'message': (
                    f'【深让可锁】缺 {",".join(missing)}；'
                    f'A 分支须同屏初盘锚+水位路径 (V17.4.40)'
                ),
            })
    return warnings


def lint_euro_deep_away(sections: list[dict], day: str | None = None) -> list[dict]:
    """
    V17.4.33 soft#8：欧冠/欧联/欧协场若方向=锁客，须写【欧战深盘客闸】行。
    （触发阈值靠分析时判断；lint 只拦「欧战场锁客却没亮闸」。）
    """
    if day and day < EURO_DEEP_AWAY_DAY:
        return []

    euro_re = re.compile(r'欧联|欧冠|欧协|欧罗巴|Europa|UCL|UEL')
    lock_away_re = re.compile(r'方向\s*=\s*锁客|二次\s*=[^\n]*→\s*锁客')
    gate_re = re.compile(r'欧战深盘客闸|soft#8')

    warnings = []
    for sec in sections:
        header = sec['header']
        blob = '\n'.join(sec['lines'])
        if not euro_re.search(header) and not euro_re.search(blob):
            continue
        if not lock_away_re.search(blob):
            continue
        if gate_re.search(blob):
            continue
        warnings.append({
            'rule': 'lint_euro_deep_away',
            'severity': 'ERROR',
            'match': header,
            'message': (
                '欧战场写了锁客，须写【欧战深盘客闸】触发=是|否（V17.4.33 soft#8；'
                '默认客不败，豁免锁客须写豁免=）'
            ),
        })
    return warnings


def lint_dual_debut_lock(sections: list[dict], day: str | None = None) -> list[dict]:
    """
    V17.4.33 soft#9：出现双新军/双方首秀叙事且方向=锁主时，须写【双新军锁主闸】。
    """
    if day and day < DUAL_DEBUT_DAY:
        return []

    debut_re = re.compile(
        r'双新军|双方.{0,12}(首秀|新军)|欧战新军.{0,20}欧战新军|'
        r'队史首次|联赛阶段新军|双方均为.{0,10}新军'
    )
    lock_home_re = re.compile(r'方向\s*=\s*锁主|二次\s*=[^\n]*→\s*锁主')
    gate_re = re.compile(r'双新军锁主闸|soft#9')

    warnings = []
    for sec in sections:
        header = sec['header']
        blob = '\n'.join(sec['lines'])
        if not debut_re.search(blob):
            continue
        if not lock_home_re.search(blob):
            continue
        if gate_re.search(blob):
            continue
        warnings.append({
            'rule': 'lint_dual_debut_lock',
            'severity': 'ERROR',
            'match': header,
            'message': (
                '双新军/双方首秀叙事下写了锁主，须写【双新军锁主闸】触发=是｜降主不败 '
                '(V17.4.33 soft#9)'
            ),
        })
    return warnings


def lint_handicap_only_channel(sections: list[dict], day: str | None = None) -> list[dict]:
    """
    V17.4.36：胜平负未开售 / 只开让球场，【出票】映射禁止写胜平负「单买主胜/复式…」；
    须见 出票通道=让球 或 映射含「让球」。
    """
    if day and day < HC_ONLY_DAY:
        return []

    unsold_re = re.compile(
        r'胜平负未开售|只开让球|JC_SP\s*=\s*未开售|JC_SP=胜平负未开售'
    )
    # 映射行里出现胜平负买法且同行/同出票块没有「让球」
    spf_buy_re = re.compile(
        r'映射[^\n]*(?:单买\s*(?:主胜|客胜|平)|复式\s*(?:主胜|客胜))'
    )
    channel_ok_re = re.compile(r'出票通道\s*=\s*让球|映射[^\n]*让球')

    warnings = []
    for sec in sections:
        header = sec['header']
        blob = '\n'.join(sec['lines'])
        if not unsold_re.search(blob):
            continue
        # 抽出票相关行
        ticket_lines = [
            ln for ln in sec['lines']
            if '【出票】' in ln or '映射' in ln or '出票通道' in ln
        ]
        ticket_blob = '\n'.join(ticket_lines) if ticket_lines else blob
        if spf_buy_re.search(ticket_blob) and not channel_ok_re.search(ticket_blob):
            warnings.append({
                'rule': 'lint_handicap_only_channel',
                'severity': 'ERROR',
                'match': header,
                'message': (
                    '胜平负未开售/只开让球场，【出票】映射禁止写单买主胜/复式胜平负；'
                    '须 出票通道=让球 且映射写让球主胜等 (V17.4.36)'
                ),
            })
            continue
        if not channel_ok_re.search(ticket_blob):
            warnings.append({
                'rule': 'lint_handicap_only_channel',
                'severity': 'ERROR',
                'match': header,
                'message': (
                    '胜平负未开售/只开让球场须写 出票通道=让球 或 映射含让球 (V17.4.36)'
                ),
            })
    return warnings


def lint_cold_upset_banner(sections: list[dict], day: str | None = None) -> list[dict]:
    """
    V17.4.37：场场须【冷门预防】触发=是|否。
    专闸已亮灯时禁止写触发=否；触发=是须命中= + 动作=。
    """
    if day and day < COLD_UPSET_DAY:
        return []

    banner_re = re.compile(r'【冷门预防】[^\n]*')
    trigger_yes = re.compile(r'触发\s*=\s*是')
    trigger_no = re.compile(r'触发\s*=\s*否')
    hit_re = re.compile(r'命中\s*=')
    action_re = re.compile(r'动作\s*=')

    lit_patterns = [
        (re.compile(r'【欧战深盘客闸】[^\n]*触发\s*=\s*是'), '欧战深盘客'),
        (re.compile(r'【双新军锁主闸】[^\n]*触发\s*=\s*是'), '双新军锁主'),
        (re.compile(r'verdict\s*=\s*(?:caution|dirty)', re.I), '深盘陷阱'),
        (re.compile(r'【状态碾压[^\n]*触发\s*=\s*是|状态碾压[^\n]*触发\s*=\s*是'), '状态碾压'),
        (re.compile(r'【跨市场背离[^\n]*触发\s*=\s*是|跨市场背离[^\n]*触发\s*=\s*是'), '跨市场背离'),
        (re.compile(r'排除\s*=[^\n]*假热'), '假热'),
        (re.compile(r'深让降维|深让锁主降维'), '深让降维'),
    ]

    warnings = []
    for sec in sections:
        header = sec['header']
        blob = '\n'.join(sec['lines'])
        m = banner_re.search(blob)
        if not m:
            warnings.append({
                'rule': 'lint_cold_upset_banner',
                'severity': 'ERROR',
                'match': header,
                'message': '须写【冷门预防】触发=是|否（V17.4.37 统一亮牌）',
            })
            continue
        line = m.group(0)
        yes = bool(trigger_yes.search(line))
        no = bool(trigger_no.search(line))
        if not yes and not no:
            warnings.append({
                'rule': 'lint_cold_upset_banner',
                'severity': 'ERROR',
                'match': header,
                'message': '【冷门预防】须含 触发=是 或 触发=否 (V17.4.37)',
            })
            continue
        if yes:
            if not hit_re.search(line) or not action_re.search(line):
                warnings.append({
                    'rule': 'lint_cold_upset_banner',
                    'severity': 'ERROR',
                    'match': header,
                    'message': '【冷门预防】触发=是 须写 命中= 与 动作= (V17.4.37)',
                })
        lit_hits = [name for pat, name in lit_patterns if pat.search(blob)]
        if lit_hits and no:
            warnings.append({
                'rule': 'lint_cold_upset_banner',
                'severity': 'ERROR',
                'match': header,
                'message': (
                    f'专闸已亮（{",".join(lit_hits)}）却写【冷门预防】触发=否；'
                    '须触发=是并命中点名 (V17.4.37)'
                ),
            })
    return warnings


def lint_hc_spf_single(sections: list[dict], day: str | None = None, filepath: str | None = None) -> list[dict]:
    """
    V17.4.38：认真拆≥1 场时，全文须有【让球稳健推荐】（或旧名【让球胜平负单选】）；
    内容为「无」或含让球主胜/让平/让负/让球客胜。允许进 B 串，禁止冒充胜平负 A 串措辞混写。
    """
    if day and day < HC_SPF_SINGLE_DAY:
        return []
    if len(sections) < 1 or not filepath:
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except OSError:
        return [{
            'rule': 'lint_hc_spf_single',
            'severity': 'ERROR',
            'match': filepath,
            'message': '无法读取文件做让球稳健推荐检查',
        }]

    warnings = []
    m = re.search(
        r'【(?:让球稳健推荐|让球胜平负单选)】([\s\S]*?)(?=\n【|\n## |\Z)',
        content,
    )
    if not m:
        warnings.append({
            'rule': 'lint_hc_spf_single',
            'severity': 'ERROR',
            'match': filepath,
            'message': '须有【让球稳健推荐】块（写「无」或≤3条；V17.4.38）',
        })
        return warnings
    body = m.group(1).strip()
    # 禁止在本块里写「主胜×客胜」这种胜平负串措辞冒充让球荐
    if re.search(r'(?<!让球)(主胜|客胜|平局)\s*[×x]\s*(?<!让)(主胜|客胜)', body):
        warnings.append({
            'rule': 'lint_hc_spf_single',
            'severity': 'ERROR',
            'match': filepath,
            'message': '【让球稳健推荐】禁止用胜平负×串冒充；让球串须写让球主胜等（V17.4.38）',
        })
    if re.search(r'^无\s*$', body, re.M) or body == '无':
        return warnings
    if not re.search(r'让球主胜|让平|让负|让球客胜', body):
        warnings.append({
            'rule': 'lint_hc_spf_single',
            'severity': 'ERROR',
            'match': filepath,
            'message': '【让球稳健推荐】非「无」时须含 让球主胜/让平/让负/让球客胜（V17.4.38）',
        })
    return warnings


def lint_summary_table(sections: list[dict], day: str | None = None, filepath: str | None = None) -> list[dict]:
    """
    V17.4.34：认真拆 ≥1 场时，全文须有固定列表头的全场汇总表。
    必含列：编号、对阵、排除、推方向、单子倾向、推比分（或主/次/防）、推进球（或进球）。
    """
    if day and day < SUMMARY_TABLE_DAY:
        return []
    if len(sections) < 1:
        return []

    path = filepath
    if not path:
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except OSError:
        return [{
            'rule': 'lint_summary_table',
            'severity': 'ERROR',
            'match': path,
            'message': '无法读取文件做汇总表检查',
        }]

    warnings = []
    # Markdown 表头一行内同时出现关键列名
    header_ok = bool(re.search(
        r'\|\s*编号\s*\|[^\n]*对阵[^\n]*排除[^\n]*推方向[^\n]*单子倾向[^\n]*(推比分|主\s*/\s*次\s*/\s*防)[^\n]*(推进球|进球)',
        content,
    ))
    # 兼容无管道、空格分隔声明
    if not header_ok:
        header_ok = bool(re.search(
            r'编号\s+对阵\s+排除\s+推方向\s+单子倾向\s+推比分',
            content,
        )) and ('推进球' in content or '进球' in content)

    if not header_ok:
        warnings.append({
            'rule': 'lint_summary_table',
            'severity': 'ERROR',
            'match': '全文',
            'message': (
                '缺【全场汇总表】固定列：编号|对阵|排除|推方向|单子倾向|推比分（主/次/防）|推进球 '
                '(V17.4.34；须在 TOP/二串一之前)'
            ),
        })
        return warnings

    # 粗检：表体行数（以 | 周四/周一… 或纯编号行）不少于认真拆场数的一半（防空表）
    body_rows = len(re.findall(r'\|\s*(周[一二三四五六日]\d{3}|\d{3})\s*\|', content))
    if body_rows < max(1, len(sections) // 2):
        warnings.append({
            'rule': 'lint_summary_table',
            'severity': 'WARN',
            'match': '全文',
            'message': f'汇总表数据行偏少（约{body_rows}行 vs 解析{len(sections)}场），请核对是否场场入表',
        })
    return warnings


def infer_winner_from_score(score: str) -> str | None:
    """从比分推断1X2结果。如 '2-1'→主胜, '1-2'→客胜, '1-1'→平。"""
    score = score.strip()
    m = re.match(r'(\d+)\s*[-:：]\s*(\d+)', score)
    if not m:
        return None
    home, away = int(m.group(1)), int(m.group(2))
    if home > away:
        return '主胜'
    elif home < away:
        return '客胜'
    else:
        return '平'


def lint_direction_score_consistency(sections: list[dict], day: str | None = None) -> list[dict]:
    """
    4.22.3 方向原子与比分三格一致性检查。
    主不败篮不得含客胜比分；客不败篮不得含主胜比分。
    """
    DIRECTION_SCORE_DAY = "2026-09-09"
    if day and day < DIRECTION_SCORE_DAY:
        return []

    allowed = {
        '锁主': {'主胜'},
        '锁客': {'客胜'},
        '锁平': {'平'},
        '主不败': {'主胜', '平'},
        '客不败': {'客胜', '平'},
        '主胜': {'主胜'},
        '客胜': {'客胜'},
        '平局': {'平'},
    }

    warnings = []
    for sec in sections:
        lines = sec['lines']
        header = sec['header']

        # 提取方向
        direction = None
        for line in lines:
            if '方向｜倾向｜比分' in line or '方向｜' in line:
                if '主不败' in line:
                    direction = '主不败'
                elif '客不败' in line:
                    direction = '客不败'
                elif '锁主' in line:
                    direction = '锁主'
                elif '锁客' in line:
                    direction = '锁客'
                elif '锁平' in line:
                    direction = '锁平'
                elif '主胜' in line and '倾向' not in line:
                    direction = '主胜'
                elif '客胜' in line and '倾向' not in line:
                    direction = '客胜'
                elif '平局' in line:
                    direction = '平局'
                break

        if not direction:
            continue

        # 提取比分（从 方向｜倾向｜比分 行或 单格 行）
        scores = []
        for line in lines:
            # 匹配 "方向｜倾向｜比分" 行中的比分
            if '方向｜倾向｜比分' in line or '方向｜' in line:
                # 提取主/次/防后面的比分，如 "2-0 主 / 1-0 次 / 1-1 防"
                score_pattern = r'(\d+\s*[-:：]\s*\d+)\s*[主次防]'
                scores = re.findall(score_pattern, line)
                if scores:
                    break
            # 匹配 "单格：2-0 / 1-0 / 1-1"
            if line.strip().startswith('单格：'):
                score_pattern = r'(\d+\s*[-:：]\s*\d+)'
                scores = re.findall(score_pattern, line)
                if scores:
                    break

        if not scores:
            continue

        # 检查每个比分是否在允许集内
        allowed_set = allowed.get(direction, set())
        for s in scores:
            winner = infer_winner_from_score(s)
            if winner and winner not in allowed_set:
                warnings.append({
                    'rule': 'lint_direction_score_consistency',
                    'severity': 'ERROR',
                    'match': header,
                    'message': f"{direction} 篮含 {s}({winner})，违反 V17.4.22.3 允许集"
                })
                break  # 一个section只报一次

    return warnings


def run_lint(filepath: str, day: str | None = None) -> dict:
    """运行全部 lint 规则，返回报告。"""
    sections = parse_sections(filepath)
    print(f"解析到 {len(sections)} 场比赛段")
    print(f"日闸: STRUCTURE_GATE={STRUCTURE_GATE_DAY}, DIR_MUST={DIR_MUST_DAY}, LEAN={LEAN_DAY}, EXCLUDE={EXCLUDE_DAY}, EXCLUDE_INTEL={EXCLUDE_INTEL_DAY}, SEASONING={SEASONING_DAY}, EURO_DEEP={EURO_DEEP_AWAY_DAY}, DUAL_DEBUT={DUAL_DEBUT_DAY}, SUMMARY={SUMMARY_TABLE_DAY}, HC_ONLY={HC_ONLY_DAY}, COLD_UPSET={COLD_UPSET_DAY}, HC_SPF_SINGLE={HC_SPF_SINGLE_DAY}, DEEP_LOCK={DEEP_LOCK_DAY}")
    print("-" * 60)

    all_warnings = []
    if not sections:
        all_warnings.append({
            'rule': 'lint_parse_sections',
            'severity': 'ERROR',
            'match': filepath,
            'message': '解析到 0 场（标题须含 vs/VS 或 周[一二三四五六日]001；0场全绿=FAIL）',
        })
        print(f"\n[lint_parse_sections] 发现 1 个问题:")
        print(f"  [ERROR] {filepath[:50]:50s} {all_warnings[0]['message']}")
    else:
        rules = [
            ("lint_low_structure_weld", lint_low_structure_weld),
            ("lint_02_atom_text", lint_02_atom_text),
            ("lint_02_must_direction", lint_02_must_direction),
            ("lint_lean_pack", lint_lean_pack),
            ("lint_exclude_three_step", lint_exclude_three_step),
            ("lint_exclude_intel_gate", lint_exclude_intel_gate),
            ("lint_seasoning_pack", lint_seasoning_pack),
            ("lint_deep_lock_receipt", lint_deep_lock_receipt),
            ("lint_euro_deep_away", lint_euro_deep_away),
            ("lint_dual_debut_lock", lint_dual_debut_lock),
            ("lint_handicap_only_channel", lint_handicap_only_channel),
            ("lint_cold_upset_banner", lint_cold_upset_banner),
            ("lint_direction_score_consistency", lint_direction_score_consistency),
            ("lint_deep_away_trap", lint_deep_away_trap),
            ("lint_form_gate", lint_form_gate),
            ("lint_both_score", lint_both_score),
            ("lint_state_crush", lint_state_crush),
            ("lint_market_divergence", lint_market_divergence),
        ]

        for name, fn in rules:
            w = fn(sections, day)
            all_warnings.extend(w)
            if w:
                print(f"\n[{name}] 发现 {len(w)} 个问题:")
                for item in w:
                    print(f"  [{item['severity']}] {item['match'][:50]:50s} {item['message']}")
            else:
                print(f"\n[{name}] ✓ 通过")

        # 汇总表需读全文（表在场次段外）
        w_sum = lint_summary_table(sections, day, filepath=filepath)
        all_warnings.extend(w_sum)
        if w_sum:
            print(f"\n[lint_summary_table] 发现 {len(w_sum)} 个问题:")
            for item in w_sum:
                print(f"  [{item['severity']}] {item['match'][:50]:50s} {item['message']}")
        else:
            print(f"\n[lint_summary_table] ✓ 通过")

        w_hc_single = lint_hc_spf_single(sections, day, filepath=filepath)
        all_warnings.extend(w_hc_single)
        if w_hc_single:
            print(f"\n[lint_hc_spf_single] 发现 {len(w_hc_single)} 个问题:")
            for item in w_hc_single:
                print(f"  [{item['severity']}] {item['match'][:50]:50s} {item['message']}")
        else:
            print(f"\n[lint_hc_spf_single] ✓ 通过")

    print("\n" + "=" * 60)
    total = len(all_warnings)
    errors = sum(1 for w in all_warnings if w['severity'] == 'ERROR')
    warns = sum(1 for w in all_warnings if w['severity'] == 'WARN')
    print(f"总计: {total} 个问题 (ERROR={errors}, WARN={warns})")

    return {
        'total': total,
        'errors': errors,
        'warnings': warns,
        'items': all_warnings,
    }



def lint_deep_away_trap(sections: list[dict], day: str | None = None) -> list[dict]:
    """
    深盘陷阱检测（V17.4.29 扩展）。
    触发条件（满足任一）但无确认书/未降级 → warn：
    1. 客队豪门 + SP_A <= 1.50
    2. 客队豪门 + 亚盘客让 >= 0.75
    3. 跨市场背离（竞彩让球盘与亚盘初盘 >= 1 档）
    """
    TRAP_DAY = "2026-09-07"
    if day and day < TRAP_DAY:
        return []

    # 导入豪门检测
    import importlib.util
    import os
    _SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location("deep_away_trap", os.path.join(_SCRIPT_DIR, "deep_away_trap.py"))
    trap_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(trap_module)
    is_big_club = trap_module.is_big_club
    DEEP_AWAY_THRESHOLD = trap_module.DEEP_AWAY_THRESHOLD
    ASIAN_HANDICAP_THRESHOLD = trap_module.ASIAN_HANDICAP_THRESHOLD

    warnings = []
    for sec in sections:
        lines = sec['lines']
        header = sec['header']
        body = sec.get('body', '')

        # 提取客队（从标题 "主队 vs 客队"；兼容 VS）
        away = None
        parts = VS_SPLIT_RE.split(header)
        if len(parts) >= 2:
            away = parts[1].strip().split('｜')[0].strip()

        if not away or not is_big_club(away):
            continue

        # 检测触发条件
        triggered = False
        trigger_reason = ""

        # 条件1: SP_A <= 1.50
        sp = None
        for line in lines:
            sp = parse_sp_line(line)
            if sp:
                break
        if sp:
            sp_h, sp_d, sp_a = sp
            if sp_a <= DEEP_AWAY_THRESHOLD:
                triggered = True
                trigger_reason = f"SP_A={sp_a:.2f}"

        # 条件2: 亚盘客让 >= 0.75
        if not triggered:
            ah_match = re.search(r'客让\s*([+-]?\d+\.?\d*)', body)
            if ah_match:
                ah = float(ah_match.group(1))
                if abs(ah) >= ASIAN_HANDICAP_THRESHOLD:
                    triggered = True
                    trigger_reason = f"亚盘客让={ah}"

        # 条件3: 跨市场背离
        if not triggered:
            if '跨市场背离' in body or '竞彩让' in body and '亚盘' in body:
                div_match = re.search(r'竞彩让\s*([+-]?\d+\.?\d*).*?亚盘.*?([+-]?\d+\.?\d*)', body)
                if div_match:
                    jc_handicap = float(div_match.group(1))
                    ah_handicap = float(div_match.group(2))
                    if abs(jc_handicap - ah_handicap) >= 1:
                        triggered = True
                        trigger_reason = f"跨市场背离:竞彩{jc_handicap}vs亚盘{ah_handicap}"

        if not triggered:
            continue

        # 检查是否有确认书或降级
        has_trap = False
        has_downgrade = False
        for line in lines:
            if '深盘陷阱' in line or '确认书' in line:
                has_trap = True
            if 'dirty' in line.lower() or '降级' in line or '不进TOP2' in line:
                has_downgrade = True

        if has_trap and has_downgrade:
            continue

        warnings.append({
            'rule': 'lint_deep_away_trap',
            'severity': 'WARN',
            'match': header,
            'away': away,
            'message': f"深盘豪门客场未做确认书/未降级: {away} ({trigger_reason})"
        })

    return warnings



def lint_ics_check(sections: list[dict], day: str | None = None) -> list[dict]:
    """P3: ICS 情报质量评分检查。"""
    if day and day < ICS_MIN_DAY:
        return []
    warnings: list[dict] = []
    for sec in sections:
        body = sec.get("body", "")
        # 简化检查：查找 ICS 标记
        has_ics = "ICS" in body or "情报质量评分" in body
        if not has_ics:
            warnings.append({
                "rule": "lint_ics_missing",
                "severity": "WARN",
                "match": sec.get("header", "")[:40],
                "message": "未写 ICS 情报质量评分 → 须补 (V17.4.24)",
            })
    return warnings


def lint_red_flags(sections: list[dict], day: str | None = None) -> list[dict]:
    """P3: 红旗清单扫描。"""
    if day and day < RED_FLAG_DAY:
        return []
    import re
    red_patterns = [
        ("RF_01", r"几乎不丢球|不丢球|零封.*稳|防线固若金汤"),
        ("RF_02", r"复仇.*必胜|讨债.*稳赢|主场.*必胜"),
        ("RF_03", r"赛程.*完全.*不利|一定.*疲劳"),
        ("RF_04", r"客队.*不可能|主队.*绝对|不可能.*输"),
        ("RF_05", r"正常.*发挥.*就赢|正常打.*就赢"),
        ("RF_06", r"虽然.*但是.*强|虽然.*不过.*必胜"),
    ]
    warnings: list[dict] = []
    for sec in sections:
        body = sec.get("body", "")
        for code, pat in red_patterns:
            if re.search(pat, body, re.IGNORECASE):
                warnings.append({
                    "rule": code,
                    "severity": "WARN",
                    "match": sec.get("header", "")[:40],
                    "message": f"红旗信号触发: {code} → 重写 (V17.4.24)",
                })
                break  # 一个section只报一次
    return warnings


def lint_form_gate(sections: list[dict], day: str | None = None) -> list[dict]:
    """
    状态评分硬闸检测（V17.4.28）。
    若 why_reject 含球星名气叙事但未附 [状态评分硬闸] 收据 → ERROR。
    """
    if day and day < FORM_GATE_DAY:
        return []
    warnings: list[dict] = []
    star_keywords = ["C罗", "梅西", "内马尔", "姆巴佩", "哈兰德", "贝林厄姆", "萨拉赫", "凯恩",
                     "球星", "头牌", "当家", "核心球员", "大腿"]
    for sec in sections:
        body = sec.get("body", "")
        # 检查是否有反剧本收据
        if "【反剧本收据】" not in body:
            continue
        # 提取 why_reject 字段内容
        why_match = re.search(r'why_reject\s*=\s*(.+?)(?:\nclause_id|\n\[|【|$)', body, re.DOTALL)
        why_text = why_match.group(1).strip() if why_match else ""
        # 检查是否以球星名气为核心
        has_star_narrative = any(kw in why_text for kw in star_keywords)
        has_form_gate = "[状态评分硬闸]" in body or "状态评分硬闸" in body
        if has_star_narrative and not has_form_gate:
            warnings.append({
                "rule": "lint_form_gate",
                "severity": "ERROR",
                "match": sec.get("header", "")[:40],
                "message": "why_reject 以球星名气为核心论据但未附 [状态评分硬闸] → 须补近5场评分收据 (V17.4.28)",
            })
    return warnings


def lint_both_score(sections: list[dict], day: str | None = None) -> list[dict]:
    """
    BOTH_SCORE 比分补偿检测（V17.4.28）。
    若触发 BOTH_SCORE 信号，防格必须含 1-1/2-1/1-2 族。
    """
    if day and day < BOTH_SCORE_DAY:
        return []
    both_score_patterns = [
        r"BOTH_SCORE.*触发",
        r"双方进球",
        r"双方.*均进球≥1",
    ]
    both_score_scores = {"1-1", "2-1", "1-2", "2-2", "3-1", "1-3"}
    warnings: list[dict] = []
    for sec in sections:
        body = sec.get("body", "")
        # 检查是否触发 BOTH_SCORE
        triggered = any(re.search(p, body) for p in both_score_patterns)
        if not triggered:
            continue
        # 提取比分推荐段
        score_section = re.search(r'【比分推荐.*?】(.+?)(?=【|$)', body, re.DOTALL)
        if not score_section:
            continue
        score_text = score_section.group(1)
        # 找主/次/防
        m = re.search(r'主/次/防\s*=\s*([^/\n]+)/([^/\n]+)/([^\n]+)', score_text)
        if not m:
            continue
        defense = m.group(3).strip()
        # 检查防格是否含双方进球比分
        has_both = any(s in defense for s in both_score_scores)
        if not has_both:
            warnings.append({
                "rule": "lint_both_score",
                "severity": "ERROR",
                "match": sec.get("header", "")[:40],
                "message": f"BOTH_SCORE 触发但防格 '{defense}' 不含双方进球比分 (1-1/2-1/1-2 族) → 须补 (V17.4.28)",
            })
    return warnings


def lint_state_crush(sections: list[dict], day: str | None = None) -> list[dict]:
    """
    状态碾压冷门预警检测（V17.4.30）。
    豪门/热门方亚盘让≥0.75 + 核心球员评分<7.0 → WARN。
    """
    if day and day < STATE_CRUSH_DAY:
        return []
    warnings: list[dict] = []
    star_keywords = ["C罗", "梅西", "内马尔", "姆巴佩", "哈兰德", "贝林厄姆", "萨拉赫", "凯恩",
                     "球星", "头牌", "当家", "核心球员", "大腿"]
    for sec in sections:
        body = sec.get("body", "")
        header = sec.get("header", "")[:40]

        # 1. 亚盘让≥0.75
        has_deep_handicap = False
        ah_match = re.search(r'(主|客)让\s*([+-]?\d+\.?\d*)', body)
        if ah_match:
            handicap = float(ah_match.group(2))
            if abs(handicap) >= 0.75:
                has_deep_handicap = True

        # 2. 核心球员评分<7.0 或状态下滑
        has_low_form = re.search(r'状态下滑|均分\s*[0-6]\.\d|评分\s*[0-6]\.\d', body)

        # 3. 有豪门/热门叙事
        has_star = any(kw in body for kw in star_keywords)

        if has_deep_handicap and has_low_form and has_star:
            has_state_crush_ack = "状态碾压" in body or ("状态下滑" in body and "降" in body)
            if not has_state_crush_ack:
                warnings.append({
                    "rule": "lint_state_crush",
                    "severity": "WARN",
                    "match": header,
                    "message": "豪门/热门方深让但核心状态下滑 → 须写状态碾压预警回应，方向不得锁热门 (V17.4.30)",
                })

    return warnings


def lint_market_divergence(sections: list[dict], day: str | None = None) -> list[dict]:
    """
    跨市场背离预警检测（V17.4.30）。
    竞彩让球盘与亚盘初盘 ≥1 档背离但未写分歧说明 → WARN。
    """
    if day and day < MARKET_DIV_DAY:
        return []
    warnings: list[dict] = []
    for sec in sections:
        body = sec.get("body", "")
        header = sec.get("header", "")[:40]

        has_divergence = "跨市场背离" in body or ("竞彩让" in body and "亚盘" in body)
        if not has_divergence:
            continue

        has_explanation = "市场分歧说明" in body or "机构分歧" in body or "竞彩深让但亚盘" in body
        if not has_explanation:
            warnings.append({
                "rule": "lint_market_divergence",
                "severity": "WARN",
                "match": header,
                "message": "跨市场背离触发但未写【市场分歧说明】→ 须补 (V17.4.30)",
            })

    return warnings


def _self_check() -> None:
    assert is_match_header('第一场 · 周四004 贝蒂斯 VS 赫塔费')
    assert is_match_header('周五001 京都 vs 柏太阳神')
    assert is_match_header('周一003 主 vs 客')
    assert not is_match_header('精选场次')
    assert not is_match_header('今晚研究 TOP')
    # V17.4.40 深让可锁收据
    bad = [{
        'header': '周日001 中国女 vs 对手',
        'lines': [
            '深让警示触线',
            '方向=锁主',
            '二次=倾斜主胜 → 锁主｜单子腿=主胜',
        ],
    }]
    w_bad = lint_deep_lock_receipt(bad, day='2026-09-22')
    assert len(w_bad) == 1 and w_bad[0]['rule'] == 'lint_deep_lock_receipt'
    good = [{
        'header': '周日001 中国女 vs 对手',
        'lines': [
            '深让警示触线',
            '方向=锁主',
            '【深让可锁】触发=是｜初盘=主-2｜水位=稳｜现盘=主-2｜依据=盘口｜档差够',
            '二次=倾斜主胜 → 锁主｜单子腿=主胜',
        ],
    }]
    assert lint_deep_lock_receipt(good, day='2026-09-22') == []
    soft = [{
        'header': '周日002 贴脸场 vs 客',
        'lines': [
            '深让警示触线',
            '方向=主不败',
            '【深让降维】触发=是｜理由=水位撤热',
        ],
    }]
    assert lint_deep_lock_receipt(soft, day='2026-09-22') == []
    print('self-check parse headers + deep_lock: ok')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="V17.4.40 日闸 lint 工具")
    parser.add_argument('file', nargs='?', help='草稿 markdown 文件路径')
    parser.add_argument('--day', help='日期阈值 (YYYY-MM-DD)，小于此日的旧稿不检查新规则', default=None)
    parser.add_argument('--self-check', action='store_true', help='解析标题自检')
    args = parser.parse_args()

    if args.self_check:
        _self_check()
        sys.exit(0)
    if not args.file:
        parser.error('需要草稿路径，或用 --self-check')

    report = run_lint(args.file, args.day)
    sys.exit(1 if report['errors'] else 0)


