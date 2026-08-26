#!/usr/bin/env bash
# V17.4.17 框架验收：intel + accuracy hooks + 可选日稿 lint
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 scripts/verify_intel_first.py
python3 scripts/verify_accuracy_hooks.py

LINT_PATH="${1:-}"
REPLAY="${REPLAY_RMA:-}"
if [[ -n "$LINT_PATH" ]]; then
  python3 scripts/lint_draft.py "$LINT_PATH" --warn-only
fi
if [[ "$REPLAY" == "1" ]]; then
  python3 scripts/replay_rma_stats.py "${DRAFTS_ROOT:-/Users/wumm/学习/@@Agent/toutiao/drafts}"
fi

echo "OK check.sh (intel + accuracy hooks${LINT_PATH:+, lint warn-only}${REPLAY:+ + replay})"
