#!/bin/bash
set -euo pipefail
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
mkdir -p logs
exec >> /Users/doyopc/AI/openclaw-factory-daemon/logs/tg_poll_min.log 2>> /Users/doyopc/AI/openclaw-factory-daemon/logs/tg_poll_min.err
while true; do
  echo "alive $(date '+%F %T')"
  sleep 5
done
