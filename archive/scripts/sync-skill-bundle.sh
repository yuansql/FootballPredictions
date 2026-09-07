#!/usr/bin/env bash
# 同步框架到 skills/.../references（供 GitHub / npx skills add）
# 默认同时装本机 Cursor（仓库 .cursor/skills + ~/.cursor/skills）
# 仅打包给别人、不要动本机时：加 --no-local
# V17.4.8：精简包 —— 不再同步一键全量/说明书/初始框架（防噪音）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REF="$ROOT/skills/football-predict-v17/references"

LOCAL=1
for arg in "$@"; do
  case "$arg" in
    --no-local) LOCAL=0 ;;
    --local-cursor) LOCAL=1 ;; # 兼容旧调用
    -h|--help)
      echo "Usage: $0 [--local-cursor|--no-local]"
      echo "  default     sync references + 本机 Cursor skill"
      echo "  --no-local  only skills/.../references（不写本机）"
      exit 0
      ;;
  esac
done

mkdir -p "$REF" "$REF/rules"

# ALWAYS（每场）+ WHEN（按联赛只开 1 个插件）+ 样例对照
FILES=(
  外部模型启动卡.txt
  球赛预测框架.txt
  p_model手算.txt
  投注分析专家_人设提示词.txt
  小联赛数据.txt
  五大联赛分析.txt
  世界杯.txt
  完整样例_体彩默认.txt
)

cd "$ROOT"

for f in "${FILES[@]}"; do
  if [[ ! -f "$ROOT/$f" ]]; then
    echo "MISSING source: $f" >&2
    exit 1
  fi
  cp "$ROOT/$f" "$REF/$f"
done

# V15.6 补丁（可执行 + 规范）
cp "$ROOT/rules/V15.6_patches.py" "$REF/rules/"
cp "$ROOT/rules/V15.6_patches.txt" "$REF/rules/"
cp "$ROOT/rules/__init__.py" "$REF/rules/"

# 也同步 skill 正文（改 SKILL.md / output-template 时必须进 references 旁的包根）
# （正文本身已在 skills/football-predict-v17/，下面拷本机）

# 清理历史噪音（若旧副本仍在 references）
rm -f \
  "$REF/一键投喂_全量合并.txt" \
  "$REF/rebuild_一键投喂.py" \
  "$REF/初始框架.txt" \
  "$REF/预测框架说明书.txt"

if [[ "$LOCAL" -eq 1 ]]; then
  CUR="$ROOT/.cursor/skills/football-predict-v17"
  mkdir -p "$CUR" "$HOME/.cursor/skills/football-predict-v17"
  cp "$ROOT/skills/football-predict-v17/SKILL.md" "$CUR/"
  cp "$ROOT/skills/football-predict-v17/output-template.md" "$CUR/"
  cp -R "$REF" "$CUR/"
  cp "$CUR/SKILL.md" "$CUR/output-template.md" "$HOME/.cursor/skills/football-predict-v17/"
  cp -R "$REF" "$HOME/.cursor/skills/football-predict-v17/"
  AGENTS="$HOME/.agents/skills/football-predict-v17"
  if [[ -d "$AGENTS" ]]; then
    cp "$CUR/SKILL.md" "$CUR/output-template.md" "$AGENTS/"
    cp -R "$REF" "$AGENTS/"
    echo "OK also synced → $AGENTS"
  fi
  echo "OK synced → $REF + 本机 Cursor ($CUR 与 ~/.cursor/skills/football-predict-v17)"
else
  echo "OK synced → $REF（精简包；含 rules/；--no-local 未装本机 Cursor）"
fi
