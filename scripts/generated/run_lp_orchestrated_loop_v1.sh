#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/../.." || exit 1
export DB_PATH="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"
export LP_VARIANT_METRICS_URL="${LP_VARIANT_METRICS_URL:-https://openclaw-fortune-order.openclaw-fortune.workers.dev/variant_metrics}"

./scripts/generated/run_lp_rewriter_v3.sh
./scripts/generated/run_lp_variant_judge_v2.sh

python3 - <<'PY'
import json
import os
import urllib.request

url = os.environ["LP_VARIANT_METRICS_URL"]
req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
with urllib.request.urlopen(req, timeout=20) as r:
    metrics = json.loads(r.read().decode("utf-8"))

print(json.dumps(metrics, ensure_ascii=False))
PY

cd deploy/fortune/pages || exit 1
/opt/homebrew/bin/wrangler pages deploy . --project-name openclaw-fortune
