#!/usr/bin/env bash
set -euo pipefail
n="${1:?pr_number}"
cd "${HOME}/AI/openclaw-factory"
source .venv/bin/activate
python -m bots.dev_reviewer_v1 --pr "$n"
