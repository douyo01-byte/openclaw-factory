#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
while true; do
  git fetch origin
  git reset --hard origin/main
  git clean -fd -e scripts -e logs
  sleep 30
done
