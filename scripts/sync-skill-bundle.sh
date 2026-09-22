#!/usr/bin/env bash
# 同步框架到 skills/.../references + 本机 Cursor/Agents skill
# 默认装本机；仅打包：--no-local
# V17.4.27：SYNC_STAMP + lint_draft 等 scripts 一并同步
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PKG="$ROOT/skills/football-predict-v17"
REF="$PKG/references"

LOCAL=1
for arg in "$@"; do
  case "$arg" in
    --no-local) LOCAL=0 ;;
    --local-cursor) LOCAL=1 ;;
    -h|--help)
      echo "Usage: $0 [--local-cursor|--no-local]"
      exit 0
      ;;
  esac
done

mkdir -p "$REF" "$REF/rules"

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
  src=""
  if [[ -f "$ROOT/$f" ]]; then
    src="$ROOT/$f"
  elif [[ -f "$ROOT/references/$f" ]]; then
    src="$ROOT/references/$f"
  elif [[ -f "$REF/$f" ]]; then
    src="$REF/$f"
  else
    echo "MISSING source: $f" >&2
    exit 1
  fi
  cp "$src" "$REF/$f"
done

# keep non-txt templates that already live in package refs (e.g. 03)
if [[ -f "$ROOT/references/03-复盘模板.md" ]]; then
  cp "$ROOT/references/03-复盘模板.md" "$REF/03-复盘模板.md"
fi

cp "$ROOT/rules/V15.6_patches.py" "$REF/rules/"
cp "$ROOT/rules/V15.6_patches.txt" "$REF/rules/"
cp "$ROOT/rules/__init__.py" "$REF/rules/"

rm -f \
  "$REF/一键投喂_全量合并.txt" \
  "$REF/rebuild_一键投喂.py" \
  "$REF/初始框架.txt" \
  "$REF/预测框架说明书.txt"

# keep package skill body in sync with repo root working copies when present
[[ -f "$ROOT/SKILL.md" ]] && cp "$ROOT/SKILL.md" "$PKG/SKILL.md"
[[ -f "$ROOT/output-template.md" ]] && cp "$ROOT/output-template.md" "$PKG/output-template.md"
[[ -f "$ROOT/防偷懒.md" ]] && cp "$ROOT/防偷懒.md" "$PKG/防偷懒.md"
[[ -f "$ROOT/SYNC_STAMP.txt" ]] && cp "$ROOT/SYNC_STAMP.txt" "$PKG/SYNC_STAMP.txt"

sync_local_skill() {
  local dest="$1"
  mkdir -p "$dest" "$dest/scripts" "$dest/references"
  cp "$PKG/SKILL.md" "$PKG/output-template.md" "$dest/"
  [[ -f "$PKG/防偷懒.md" ]] && cp "$PKG/防偷懒.md" "$dest/"
  [[ -f "$PKG/SYNC_STAMP.txt" ]] && cp "$PKG/SYNC_STAMP.txt" "$dest/"
  cp -R "$REF/." "$dest/references/"
  for s in lint_draft.py structure_gate.py deep_away_trap.py gen_rma_detail_table.py; do
    [[ -f "$ROOT/scripts/$s" ]] && cp "$ROOT/scripts/$s" "$dest/scripts/"
  done
  # 清理下游已废除的脚本，避免幽灵文件
  rm -f "$dest/scripts/backtest_structure_gate.py" \
        "$dest/scripts/clause_heatmap.py" \
        "$dest/scripts/score_geometry.py" \
        "$dest/scripts/intelligence_checklist.py" \
        "$dest/scripts/red_flag_scanner.py" \
        "$dest/references/trap_confirmation_template.md"
}

if [[ "$LOCAL" -eq 1 ]]; then
  CUR="$ROOT/.cursor/skills/football-predict-v17"
  sync_local_skill "$CUR"
  sync_local_skill "$HOME/.cursor/skills/football-predict-v17"
  AGENTS="$HOME/.agents/skills/football-predict-v17"
  mkdir -p "$AGENTS"
  sync_local_skill "$AGENTS"
  echo "OK also synced → $AGENTS"
  echo "OK synced → $REF + 本机 Cursor ($CUR 与 ~/.cursor/skills/football-predict-v17)"
else
  echo "OK synced → $REF（--no-local 未装本机）"
fi
