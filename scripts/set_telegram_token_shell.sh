#!/usr/bin/env bash
set -euo pipefail
tok="${1:?token}"
export TELEGRAM_BOT_TOKEN="$tok"
python -m bots.tg_inbox_poll_v1
