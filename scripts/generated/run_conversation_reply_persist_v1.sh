#!/bin/bash
set -euo pipefail
cd "$HOME/AI/openclaw-factory-daemon" || exit 1
export DB_PATH="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"
exec python3 bots/conversation_reply_persist_v1.py
