#!/usr/bin/env bash
set -euo pipefail
cd "${HOME}/AI/openclaw-factory"
source .venv/bin/activate
python -m bots.dev_reviewer_v1 --pr "${1:?pr_number}"
