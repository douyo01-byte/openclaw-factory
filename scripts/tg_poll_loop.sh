#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
export PYTHONPATH=$PWD
while true; do
  python bots/ingest_telegram_replies_v1.py
  sleep 10
done
