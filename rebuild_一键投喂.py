#!/usr/bin/env python3
"""重建 一键投喂_全量合并.txt（改完分文件后跑一次）"""
from pathlib import Path
from datetime import datetime

root = Path(__file__).resolve().parent

parts = [
    ("00_强制硬闸", "外部模型启动卡.txt", "ALWAYS · 最高优先级 · 先读完再往下"),
    ("01_主控", "球赛预测框架.txt", "ALWAYS · 每场必用"),
    ("01b_V15.6补丁", "rules/V15.6_patches.txt", "ALWAYS · 五补丁永久挂载；与主控 [V15.6_PATCHES] 同文"),
    ("02_底盘", "初始框架.txt", "ALWAYS · 方向/BLOWOUT/禁默认1-1"),
    ("03_手算", "p_model手算.txt", "ALWAYS · 算 Edge 前必用"),
    ("04_出票人设", "投注分析专家_人设提示词.txt", "ALWAYS · 出票格式/星级"),
    ("05_小联赛插件", "小联赛数据.txt", "WHEN · 挪超/芬超/瑞超/爱甲/捷甲等无 Understat"),
    ("06_五大联赛插件", "五大联赛分析.txt", "WHEN · 仅英西德意法 + 有 Understat"),
    ("07_杯赛插件", "世界杯.txt", "WHEN · 仅世界杯/欧洲杯决赛圈"),
    ("08_样例对照", "完整样例_体彩默认.txt", "REF · 可介入/弃单长什么样"),
    ("09_说明书", "预测框架说明书.txt", "REF · SOP；与硬闸冲突以硬闸+主控为准"),
]

header = """# 2足球框架 · 一键投喂（全量合并）
#
# 用法（千问 / DeepSeek / ChatGPT / Claude）：
#   1) 整份上传或粘贴本文件到「系统提示 / 知识库 / 长上下文」
#   2) 用户消息只写对阵+赔率+「按框架预测」
#   3) 模型必须先执行【00_强制硬闸】，再按联赛只「激活」对应 WHEN 章节
#
# ★ 关键：全量合并 ≠ 全章节同时生效
#   - ALWAYS 章节：每场都约束
#   - WHEN 章节：未命中联赛类型时禁止引用其高阶指标（如挪超禁止用五大 xT）
#   - 输出缺【硬闸自检】【出票】【投注星级】= 废稿
#
# 维护：改完各分文件后，在本目录执行：
#   python3 rebuild_一键投喂.py
#
# 生成时间见文末。
#
"""

blocks = [header]
for tag, fname, note in parts:
    path = root / fname
    if not path.exists():
        raise SystemExit(f"missing: {fname}")
    body = path.read_text(encoding="utf-8")
    banner = f"""
═══════════════════════════════════════════════════════════════════════════════
■ 分卷 {tag} · 源文件：{fname}
■ 生效：{note}
═══════════════════════════════════════════════════════════════════════════════

"""
    blocks.append(banner + body.rstrip() + "\n")

footer = f"""
═══════════════════════════════════════════════════════════════════════════════
■ END OF BUNDLE
■ generated_at={datetime.now().strftime('%Y-%m-%d %H:%M')}
■ source_files={len(parts)}
═══════════════════════════════════════════════════════════════════════════════
"""
blocks.append(footer)

out = root / "一键投喂_全量合并.txt"
out.write_text("\n".join(blocks), encoding="utf-8")
print(f"OK → {out.name} ({out.stat().st_size} bytes)")
