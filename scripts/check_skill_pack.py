#!/usr/bin/env python3
"""瘦身后自检：lint 查的【标记】与 SKILL 指向的文件都必须在包内可找到。"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LEGACY = {"【(?:让球稳健推荐|让球胜平负单选)】", "【方向三步】", "【比分推荐.*?】", "【让球胜平负单选】"}
FIELDS = ["交卷模式=", "初盘=", "冻排=", "情报档=", "排除=", "质疑=", "弱置信=", "对照盘口修订=",
          "λ校准=", "出票通道=", "预算=", "豁免=", "席=", "买=", "盘口=", "荐="]

skill = (ROOT / "SKILL.md").read_text()
pack = skill + (ROOT / "output-template.md").read_text()
pack += "".join(p.read_text() for p in (ROOT / "references").glob("*.md"))
lint = (ROOT / "scripts/lint_draft.py").read_text()

errors = [f"marker missing: {t}" for t in sorted(set(re.findall(r"【[^】\\\s]{1,20}】", lint)) - LEGACY)
          if t not in pack]
errors += [f"field missing in SKILL: {f}" for f in FIELDS if f not in skill]
for ref in set(re.findall(r"`((?:references|scripts|rules)/[^`\s]+)`", skill)):
    if not (ROOT / ref).exists():
        errors.append(f"broken ref: {ref}")

print("\n".join(errors) or "OK")
sys.exit(1 if errors else 0)
