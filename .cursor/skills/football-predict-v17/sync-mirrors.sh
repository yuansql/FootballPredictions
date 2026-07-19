#!/usr/bin/env bash
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
cp "$SRC/SKILL.md" "$SRC/output-template.md" /Users/wumm/.cursor/skills/football-predict-v17/
mkdir -p /Users/wumm/学习/AQQ/.cursor/skills/football-predict-v17
cp "$SRC/SKILL.md" "$SRC/output-template.md" /Users/wumm/学习/AQQ/.cursor/skills/football-predict-v17/
echo "synced mirrors from $SRC"
