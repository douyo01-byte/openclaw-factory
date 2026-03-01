#!/usr/bin/env bash
set -euo pipefail
while true; do
  python3 bots/ingest_telegram_replies_v1.py
  sleep 10
done
