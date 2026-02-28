#!/usr/bin/env bash
set -euo pipefail
cd "${HOME}/AI/openclaw-factory"
source .venv/bin/activate
python -m bots.dev_reviewer_v1 --limit "${1:-10}"
