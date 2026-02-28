#!/usr/bin/env bash
set -euo pipefail
launchctl getenv TELEGRAM_BOT_TOKEN || true
launchctl getenv BOT_TOKEN || true
env | grep -E '^TELEGRAM_BOT_TOKEN=|^BOT_TOKEN=' || true
