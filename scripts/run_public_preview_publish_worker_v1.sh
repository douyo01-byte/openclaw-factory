#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
export DB_PATH="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"
export TELEGRAM_OS_PUBLIC_REPO="${TELEGRAM_OS_PUBLIC_REPO:-$HOME/AI/telegram-os-public}"
export TELEGRAM_OS_PUBLIC_BASE_URL="${TELEGRAM_OS_PUBLIC_BASE_URL:-https://douyo01-byte.github.io/telegram-os-public}"
python3 bots/public_preview_publish_worker_v1.py
