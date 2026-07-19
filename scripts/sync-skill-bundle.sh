#!/usr/bin/env bash
# 同步框架到 skills/.../references（供 GitHub / npx skills add）
# 默认不安装到本机 ~/.cursor/skills
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REF="$ROOT/skills/football-predict-v17/references"

mkdir -p "$REF"

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

# 仅当显式传 --local-cursor 才装到本机（默认不装）
if [[ "${1:-}" == "--local-cursor" ]]; then
  CUR="$ROOT/.cursor/skills/football-predict-v17"
  mkdir -p "$CUR" "$HOME/.cursor/skills/football-predict-v17"
  cp "$ROOT/skills/football-predict-v17/SKILL.md" "$CUR/"
  cp "$ROOT/skills/football-predict-v17/output-template.md" "$CUR/"
  cp "$CUR/SKILL.md" "$CUR/output-template.md" "$HOME/.cursor/skills/football-predict-v17/"
  echo "OK synced → $REF + local Cursor ($CUR)"
else
  echo "OK synced → $REF（未安装本机 Cursor；需要时加 --local-cursor）"
fi
