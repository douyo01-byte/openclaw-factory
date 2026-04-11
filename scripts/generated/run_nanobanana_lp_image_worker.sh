#!/bin/bash
set -euo pipefail
cd "$HOME/AI/openclaw-factory-daemon" || exit 1
export DB_PATH="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"
[ -f env/openai.env ] && source env/openai.env || true
[ -f env/gemini.env ] && source env/gemini.env || true
exec "$HOME/AI/openclaw-factory-daemon/.venv/bin/python" bots/nanobanana_lp_image_worker.py "$@"
