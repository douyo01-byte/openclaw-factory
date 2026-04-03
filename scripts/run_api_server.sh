#!/bin/bash
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
exec /usr/bin/python3 api_server.py
