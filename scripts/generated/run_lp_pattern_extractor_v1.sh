#!/bin/bash
set -euo pipefail
cd "$HOME/AI/openclaw-factory-daemon" || exit 1
export DB_PATH="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"
exec "$HOME/AI/openclaw-factory-daemon/.venv/bin/python" bots/lp_pattern_extractor_v1.py
