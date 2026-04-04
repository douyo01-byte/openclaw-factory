#!/bin/bash
set -euo pipefail

ROOT="${HOME}/AI/openclaw-factory-daemon"
DB_PATH="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"
cd "$ROOT" || exit 1

echo "== deploy_safe =="

echo "-- git status --"
git status -sb || true

echo "-- db check --"
sqlite3 "$DB_PATH" "pragma quick_check;" || true

echo "-- api health --"
if ! curl -fsS http://127.0.0.1:5001/health >/dev/null; then
  echo "api down -> restart"

  launchctl kickstart -k "gui/$(id -u)/jp.openclaw.api_server" || true
  sleep 3

  if ! curl -fsS http://127.0.0.1:5001/health >/dev/null; then
    echo "api restart failed"
    exit 1
  fi
fi

echo "-- telegram executor check --"
if ! launchctl list | grep -q telegram_ops_executor_v1; then
  echo "executor down -> restart skipped inside executor task"
fi

echo "-- router worker check --"
launchctl kickstart -k "gui/$(id -u)/jp.openclaw.kaikun04_router_worker_v1" || true

echo "-- final health --"
curl -fsS http://127.0.0.1:5001/health || exit 1

echo "deploy_safe_done"
