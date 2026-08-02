#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证 V17.4.9 INTEL_FIRST + 双轨推荐精简包：关键短语 + 样例顺序 + 噪音已删。"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PHRASES = {
    "skills/football-predict-v17/SKILL.md": [
        "INTEL_FIRST",
        "V17.4.9",
        "精简包",
        "【情报叙事】",
        "【球队画像】",
        "【比赛剧本】",
        "【研究推荐】",
        "盘口辅助",
        "禁止：先盯 SP/Edge",
        "Edge 诚实",
        "胜平负",
        "进球数",
        "比分",
    ],
    "skills/football-predict-v17/output-template.md": [
        "【情报叙事】",
        "【球队画像】",
        "【比赛剧本】",
        "【研究推荐】",
        "取证 → 情报 → 球队 → 剧本 → 硬闸/Edge",
        "胜平负",
        "进球数",
        "比分",
    ],
    "球赛预测框架.txt": ["[INTEL_FIRST", "球队叙事优先", "[STAR_RATING", "【研究推荐】", "V17.4.9"],
    "投注分析专家_人设提示词.txt": [
        "INTEL_FIRST",
        "你先讲球，再谈票",
        "【情报叙事】",
        "【研究推荐】",
        "V17.4.9",
    ],
    "外部模型启动卡.txt": [
        "INTEL_FIRST",
        "【情报叙事】",
        "禁止先盯 SP",
        "精简包",
        "已废除",
        "【研究推荐】",
        "V17.4.9",
    ],
    "完整样例_体彩默认.txt": [
        "【情报叙事】",
        "【球队画像】",
        "【比赛剧本】",
        "出票闸",
        "【研究推荐】",
    ],
    "使用.md": ["INTEL_FIRST", "V17.4.9", "精简包", "已废除", "双轨推荐"],
    "README.md": ["V17.4.9", "精简包", "双轨推荐"],
}

ORDER_MARKERS = ["【取证清单】", "【情报叙事】", "【球队画像】", "【比赛剧本】", "【Edge"]

NOISE_MUST_ABSENT = [
    "一键投喂_全量合并.txt",
    "rebuild_一键投喂.py",
    "初始框架.txt",
    "预测框架说明书.txt",
]


def main() -> int:
    fails = []
    for rel, phrases in REQUIRED_PHRASES.items():
        path = ROOT / rel
        if not path.is_file():
            fails.append(f"MISSING {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        for p in phrases:
            if p not in text:
                fails.append(f"NO_PHRASE {rel} :: {p}")

    sample = (ROOT / "完整样例_体彩默认.txt").read_text(encoding="utf-8")
    block = sample.split("## 样例 B")[0]
    idxs = []
    for m in ORDER_MARKERS:
        i = block.find(m)
        if i < 0:
            fails.append(f"SAMPLE_A_MISSING {m}")
        idxs.append(i)
    if all(i >= 0 for i in idxs) and idxs != sorted(idxs):
        fails.append(f"SAMPLE_A_ORDER_BAD {list(zip(ORDER_MARKERS, idxs))}")
    if "【研究推荐】" not in block:
        fails.append("SAMPLE_A_MISSING_RESEARCH_REC")
    if "【研究推荐】" not in sample.split("## 样例 B", 1)[-1]:
        fails.append("SAMPLE_B_MISSING_RESEARCH_REC")

    skill = (ROOT / "skills/football-predict-v17/SKILL.md").read_text(encoding="utf-8")
    if "V17.4.9" not in skill:
        fails.append("SKILL_VERSION_NOT_1749")

    if re.search(r"作业流[\s\S]{0,200}Edge_eff", skill) and "情报叙事" not in skill.split("## 作业流")[1][:400]:
        fails.append("SKILL_JOBFLOW_STILL_EDGE_FIRST")

    bound = (ROOT / "rules/V15.6_patches.py").read_text(encoding="utf-8")
    if 'BOUND_TO = "V17.4.9"' not in bound:
        fails.append("PATCHES_BOUND_NOT_1749")

    for name in NOISE_MUST_ABSENT:
        for base in (ROOT, ROOT / "skills/football-predict-v17/references"):
            p = base / name
            if p.exists():
                fails.append(f"NOISE_STILL_PRESENT {p.relative_to(ROOT)}")

    for name in (
        "外部模型启动卡.txt",
        "球赛预测框架.txt",
        "p_model手算.txt",
        "投注分析专家_人设提示词.txt",
        "完整样例_体彩默认.txt",
        "小联赛数据.txt",
    ):
        if not (ROOT / "skills/football-predict-v17/references" / name).is_file():
            fails.append(f"REF_MISSING {name}")

    if fails:
        print("FAIL")
        for f in fails:
            print(" -", f)
        return 1
    print("PASS INTEL_FIRST + dual-recommend slim-pack checks")
    print("OK files=", len(REQUIRED_PHRASES), "noise_gone=", len(NOISE_MUST_ABSENT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
