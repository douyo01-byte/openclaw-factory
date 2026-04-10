#!/bin/bash
set -euo pipefail
cd "$HOME/AI/openclaw-factory-daemon" || exit 1
export DB_PATH="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"
export LP_VARIANT_METRICS_URL="${LP_VARIANT_METRICS_URL:-https://openclaw-fortune-order.openclaw-fortune.workers.dev/variant_metrics}"
exec "$HOME/AI/openclaw-factory-daemon/.venv/bin/python" bots/lp_variant_judge_v2.py
