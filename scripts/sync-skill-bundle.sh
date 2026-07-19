#!/usr/bin/env bash
# 把仓库根目录框架文件同步进 skills/.../references 与 .cursor/skills
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REF="$ROOT/skills/football-predict-v17/references"
CUR="$ROOT/.cursor/skills/football-predict-v17"

mkdir -p "$REF" "$CUR"

FILES=(
  外部模型启动卡.txt
  球赛预测框架.txt
  初始框架.txt
  p_model手算.txt
  投注分析专家_人设提示词.txt
  小联赛数据.txt
  五大联赛分析.txt
  世界杯.txt
  完整样例_体彩默认.txt
  预测框架说明书.txt
  一键投喂_全量合并.txt
  rebuild_一键投喂.py
)

cd "$ROOT"
python3 rebuild_一键投喂.py

for f in "${FILES[@]}"; do
  cp "$ROOT/$f" "$REF/$f"
done

cp "$ROOT/skills/football-predict-v17/SKILL.md" "$CUR/SKILL.md"
cp "$ROOT/skills/football-predict-v17/output-template.md" "$CUR/output-template.md"

# 可选：同步到本机 Cursor / 上级 AQQ（失败忽略）
mkdir -p "$HOME/.cursor/skills/football-predict-v17" 2>/dev/null || true
cp "$CUR/SKILL.md" "$CUR/output-template.md" "$HOME/.cursor/skills/football-predict-v17/" 2>/dev/null || true
mkdir -p "$ROOT/../.cursor/skills/football-predict-v17" 2>/dev/null || true
cp "$CUR/SKILL.md" "$CUR/output-template.md" "$ROOT/../.cursor/skills/football-predict-v17/" 2>/dev/null || true

echo "OK synced → $REF and $CUR"
