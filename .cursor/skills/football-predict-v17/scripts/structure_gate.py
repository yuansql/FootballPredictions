#!/usr/bin/env python3
"""
structure_gate.py — V17.4.100 低结构平优先闸 + 镜像场量化闸

功能：
1. 根据竞彩 SP (主/平/客) 计算结构风险标签
2. 低结构仅提示风险，不按较低 SP 强制输出不败或倾向
3. 历史复盘：只列出结构信号，不模拟方向变化或准确率
4. 镜像场闸（V17.4.100）：λ_H 与 λ_A 相对差 <10% → 方向只能观望/平局打底，
   禁按叙事冻主不败/客不败。依据：2026-11-23 蒙扎(λ2.04/2.02 冻客不败, 3-0 穿)
   与 08-27 塞尔塔/费伦茨同族（V17.4.99「分不清不得硬装」的量化落地）。

用法：
    python3 structure_gate.py --backtest <复盘文件.md>
    python3 structure_gate.py --tag <P_H> <P_D> <P_A>
    python3 structure_gate.py --mirror <λ_H> <λ_A>
    python3 structure_gate.py --lint <草稿文件.md>

阈值（可调）：
    DRAW_PRIORITY_THRESHOLD = 0.10   # |P_H - P_A| < 10% → draw_priority
    LOW_STRUCTURE_EPSILON = 0.15     # 传统低结构阈值
    MIRROR_LAMBDA_THRESHOLD = 0.10   # |λ_H-λ_A|/max(λ) < 10% → 镜像场
"""

import sys
import re
import argparse
from typing import Tuple, Literal

# === 可调阈值 ===
DRAW_PRIORITY_THRESHOLD = 0.10   # |P(主) - P(客)| < 10% → 平优先闸
LOW_STRUCTURE_EPSILON = 0.15     # 传统低结构判定
MIRROR_LAMBDA_THRESHOLD = 0.10   # λ 相对差 < 10% → 镜像场（V17.4.100）

# === 结构标签枚举 ===
StructureTag = Literal["high_structure", "low_structure", "draw_priority"]


def compute_structure_tag(sp_h: float, sp_d: float, sp_a: float) -> StructureTag:
    """
    根据 SP 值（体彩赔率）计算结构标签。

    规则（V17.4.23）——基于赔率而非概率：
    1. 双方 SP 都 >2.0 且 |SP_H - SP_A| < 1.5 → draw_priority（实力接近，平局概率高）
    2. SP_D < 3.0 → draw_priority（庄家认可平局概率不低）
    3. max(SP_H, SP_A) / min(SP_H, SP_A) < 1.8 → draw_priority（赔率比接近）
    4. 否则 → high_structure（允许锁单）
    """
    # 条件1：双方都不是极低赔，且差距小
    both_not_fav = sp_h > 2.0 and sp_a > 2.0
    close_spread = abs(sp_h - sp_a) < 1.5

    # 条件2：庄家认为平局概率不低（SP_D < 3.0 意味着平局概率 >33%）
    draw_respected = sp_d < 3.0

    # 条件3：赔率比接近（没有一方被极度看好）
    ratio = max(sp_h, sp_a) / min(sp_h, sp_a) if min(sp_h, sp_a) > 0 else 999
    close_ratio = ratio < 1.8

    if (both_not_fav and close_spread) or draw_respected or close_ratio:
        return "draw_priority"
    else:
        return "high_structure"


def get_enforced_direction(sp_h: float, sp_d: float, sp_a: float) -> Tuple[str, str] | Tuple[None, None]:
    """
    返回 (方向原子, 单子倾向) 的强制输出。

    当前规则 V17.4.99：赔率结构只作风险提示，不强制任何方向。
    返回 (None, None)；需由硬情报单独决定方向，没有一侧则观望。
    """
    # 保留旧接口供历史回测调用，但禁止市场价格直接生成方向。
    return None, None


def mirror_gate(lam_h: float, lam_a: float) -> bool:
    """
    镜像场闸（V17.4.100）：λ_H 与 λ_A 相对差 < MIRROR_LAMBDA_THRESHOLD。

    镜像场 = 量化意义上的「没有优势侧」（V17.4.99 的判据落地）：
    方向只能观望（或用户指定时平局打底），禁按叙事冻主不败/客不败。
    """
    if lam_h <= 0 or lam_a <= 0:
        return False
    rel = abs(lam_h - lam_a) / max(lam_h, lam_a)
    return rel < MIRROR_LAMBDA_THRESHOLD


def parse_sp_line(line: str) -> Tuple[float, float, float] | None:
    """从一行文本中提取三个主盘 SP 值（忽略括号内的让球 SP）。"""
    # 只处理包含 "SP" 关键字的行
    if 'SP' not in line:
        return None
    # 跳过未开售/无数据行
    if '未开售' in line or '无数据' in line or 'N/A' in line:
        return None
    # 去掉括号及其内容，避免捕获让球 SP
    cleaned = re.sub(r'（[^）]*）', '', line)
    # 提取所有数字（兼容 **3.00** 和 1.38 两种格式）
    nums = re.findall(r'(?<![\d.])\d+\.\d+(?![\d.])', cleaned)
    if len(nums) >= 3:
        vals = [float(nums[0]), float(nums[1]), float(nums[2])]
        # 防御：SP 值应均 >1.0；若全部 <1.0 则为 path weight 误捕
        if all(v < 1.0 for v in vals):
            return None
        return vals[0], vals[1], vals[2]
    return None


def parse_markdown_backtest(filepath: str) -> list[dict]:
    """
    从复盘 markdown 中解析比赛数据。
    返回列表，每项含：name, p_h, p_d, p_a, predicted_direction, actual_result
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    matches = []
    # 按 "## " 分割比赛段
    sections = re.split(r'\n## ', content)

    for sec in sections:
        lines = sec.strip().split('\n')
        if not lines:
            continue

        # 提取比赛名称
        header = lines[0].strip().lstrip('#').strip()
        if '复盘' in header or '附录' in header or '总体' in header:
            continue

        # 提取 SP
        sp = None
        for line in lines:
            sp = parse_sp_line(line)
            if sp:
                break

        # 提取预测方向
        pred_dir = None
        for line in lines:
            if '方向｜倾向｜比分' in line or '方向｜' in line:
                if '主不败' in line:
                    pred_dir = '主不败'
                elif '客不败' in line:
                    pred_dir = '客不败'
                break

        # 提取实际比分（从复盘表行中提取）
        actual = None
        for line in lines:
            if re.search(r'\*\*\d+-\d+\*\*', line):
                m = re.search(r'\*\*(\d+)-(\d+)\*\*', line)
                if m:
                    actual = (int(m.group(1)), int(m.group(2)))
                    break

        matches.append({
            'name': header[:60],
            'sp': sp,
            'predicted_direction': pred_dir,
            'actual': actual,
        })

    return matches


def run_backtest(filepath: str) -> None:
    """运行回测，输出启用闸前后的方向变化统计。"""
    matches = parse_markdown_backtest(filepath)
    print(f"解析到 {len(matches)} 场比赛\n")

    draw_priority_count = 0

    for m in matches:
        if not m['sp']:
            continue

        p_h, p_d, p_a = m['sp']
        tag = compute_structure_tag(p_h, p_d, p_a)

        if tag == "draw_priority":
            draw_priority_count += 1
            print(f"  [draw_priority] {m['name'][:50]:50s} "
                  f"SP:{p_h:.2f}/{p_d:.2f}/{p_a:.2f} |diff|={abs(p_h-p_a):.2f} "
                  "→ 结构风险提示，不能推断方向")

    print(f"\n=== 回测统计 ===")
    print(f"draw_priority 触发场次: {draw_priority_count}")
    print("本脚本不重算赛前方向或准确率；需另用冻结的赛前记录评估")
    print("阈值：见 compute_structure_tag 的 SP 条件；此处不衡量预测改进")


def run_tag(p_h: float, p_d: float, p_a: float) -> None:
    """单场比赛标签计算。"""
    tag = compute_structure_tag(p_h, p_d, p_a)
    print(f"SP: {p_h:.2f} / {p_d:.2f} / {p_a:.2f}")
    print(f"|SP_H - SP_A| = {abs(p_h - p_a):.3f}")
    print(f"结构标签: {tag}")
    print("结构只提示风险；方向须由硬情报决定，无一侧则观望")


def run_lint(filepath: str) -> None:
    """扫描草稿文件，检测低结构硬焊问题。"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    warnings = 0
    sections = re.split(r'\n## ', content)

    for sec in sections:
        lines = sec.strip().split('\n')
        if not lines:
            continue
        header = lines[0].strip().lstrip('#').strip()

        # 提取 SP
        sp = None
        for line in lines:
            sp = parse_sp_line(line)
            if sp:
                break
        if not sp:
            continue

        p_h, p_d, p_a = sp
        tag = compute_structure_tag(p_h, p_d, p_a)

        # 检查是否硬焊
        direction_line = None
        for line in lines:
            if '方向｜倾向｜比分' in line:
                direction_line = line
                break

        if tag in ("draw_priority", "low_structure") and direction_line:
            # 检测：draw_priority 但倾向写了主胜/客胜/锁平
            if tag == "draw_priority":
                if '主胜' in direction_line or '客胜' in direction_line or '锁平' in direction_line:
                    print(f"[WARN] 低结构焊死倾向: {header[:50]}")
                    print(f"       SP:{p_h:.2f}/{p_d:.2f}/{p_a:.2f} |diff|={abs(p_h-p_a):.2f}")
                    print(f"       原文: {direction_line[:100]}")
                    warnings += 1

        # === 镜像场量化闸（V17.4.100） ===
        lam_m_h = None
        lam_m_a = None
        for line in lines:
            m_h = re.search(r'λ_H\s*=\s*(\d+(?:\.\d+)?)', line)
            m_a = re.search(r'λ_A\s*=\s*(\d+(?:\.\d+)?)', line)
            if m_h and m_a:
                lam_m_h, lam_m_a = float(m_h.group(1)), float(m_a.group(1))
                break
        if lam_m_h and lam_m_a and mirror_gate(lam_m_h, lam_m_a):
            # 找方向行（兼容 方向= / 冻向= 两种写法）
            dir_word = None
            for line in lines:
                m = re.search(r'(?:方向|冻向)\s*=\s*(锁主|锁客|锁平|主不败|客不败|观望)', line)
                if m:
                    dir_word = m.group(1)
                    break
            if dir_word in ('主不败', '客不败', '锁主', '锁客'):
                rel = abs(lam_m_h - lam_m_a) / max(lam_m_h, lam_m_a) * 100
                print(f"[ERROR] 镜像场禁单边档: {header[:50]}")
                print(f"        λ_H={lam_m_h:.2f}/λ_A={lam_m_a:.2f} 相对差 {rel:.1f}%"
                      f"（<{MIRROR_LAMBDA_THRESHOLD*100:.0f}%）却冻 {dir_word}")
                print(f"        只许观望或平局打底；须写一行 λ_mirror=触发｜相对差={rel:.1f}%（V17.4.100）")
                warnings += 1

    print(f"\n=== lint 结果 ===")
    print(f"警告数: {warnings}")
    if warnings == 0:
        print("未发现低结构硬焊/镜像场压边问题 ✓")


def run_mirror(lam_h: float, lam_a: float) -> None:
    """单场镜像场判定。"""
    rel = abs(lam_h - lam_a) / max(lam_h, lam_a) * 100
    is_mirror = mirror_gate(lam_h, lam_a)
    print(f"λ_H={lam_h:.2f} / λ_A={lam_a:.2f}")
    print(f"相对差: {rel:.1f}%（阈值 {MIRROR_LAMBDA_THRESHOLD*100:.0f}%）")
    if is_mirror:
        print("判定: 镜像场 → 方向只能观望或平局打底，禁主不败/客不败叙事档（V17.4.100）")
        print("触发时正文须写一行 λ_mirror=触发｜相对差=X%")
    else:
        print("判定: 非镜像场，方向档不受镜像闸限制")


# === CLI ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="V17.4.100 低结构平优先闸 + 镜像场量化闸")
    sub = parser.add_subparsers(dest='cmd')

    p_backtest = sub.add_parser('backtest', help='对复盘文件跑回测')
    p_backtest.add_argument('file', help='复盘 markdown 文件路径')

    p_tag = sub.add_parser('tag', help='单场比赛标签计算')
    p_tag.add_argument('p_h', type=float, help='主胜概率/SP')
    p_tag.add_argument('p_d', type=float, help='平局概率/SP')
    p_tag.add_argument('p_a', type=float, help='客胜概率/SP')

    p_mirror = sub.add_parser('mirror', help='单场镜像场判定')
    p_mirror.add_argument('lam_h', type=float, help='λ_H')
    p_mirror.add_argument('lam_a', type=float, help='λ_A')

    p_lint = sub.add_parser('lint', help='扫描草稿文件')
    p_lint.add_argument('file', help='草稿 markdown 文件路径')

    args = parser.parse_args()

    if args.cmd == 'backtest':
        run_backtest(args.file)
    elif args.cmd == 'tag':
        run_tag(args.p_h, args.p_d, args.p_a)
    elif args.cmd == 'mirror':
        run_mirror(args.lam_h, args.lam_a)
    elif args.cmd == 'lint':
        run_lint(args.file)
    else:
        # 默认：演示几个关键场
        print("=== 周末关键场 structure_gate 演示 ===\n")
        demo_cases = [
            ("汉诺威 vs 卡尔斯鲁厄 (2-2平局miss)", 1.38, 4.60, 5.35),
            ("鹿斯巴达 vs 兹沃勒 (2-2平局miss)", 1.72, 3.80, 3.51),
            ("纽卡斯尔 vs 伯恩茅斯 (2-2平局miss)", 2.03, 3.55, 2.82),
            ("赫尔城 vs 维拉 (0-0平局miss)", 2.48, 3.33, 2.35),
            ("纽约城 vs 纳什维尔 (0-0平局miss)", 2.48, 3.33, 2.35),
            ("贝蒂斯 vs 皇马 (1-0主胜冷门)", 6.30, 5.30, 1.28),
            ("巴黎 vs 摩纳哥 (1-2客胜冷门)", 1.22, 5.35, 8.15),
            ("里昂 vs 欧塞尔 (3-1命中)", 1.32, 4.50, 6.70),
        ]
        for name, p_h, p_d, p_a in demo_cases:
            tag = compute_structure_tag(p_h, p_d, p_a)
            marker = "⚠️" if tag == "draw_priority" else " "
            print(f"{marker} {name}")
            print(f"   SP:{p_h:.2f}/{p_d:.2f}/{p_a:.2f} |diff|={abs(p_h-p_a):.2f} → {tag}")
            print("   仅风险提示，不强制方向")
            print()
