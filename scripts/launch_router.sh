#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
export PYTHONPATH=$PWD
export PYTHONUNBUFFERED=1
while true; do
  python bots/chat_router_v1.py
  sleep 5
done
