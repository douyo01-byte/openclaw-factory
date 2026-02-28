#!/usr/bin/env bash
set -euo pipefail
tok="${1:?token}"
launchctl setenv TELEGRAM_BOT_TOKEN "$tok"
echo "OK"
