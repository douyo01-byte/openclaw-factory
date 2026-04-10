#!/bin/bash
set -euo pipefail

cd "$HOME/AI/openclaw-factory-daemon" || exit 1
export DB_PATH="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"
export LP_VARIANT_METRICS_URL="${LP_VARIANT_METRICS_URL:-https://openclaw-fortune-order.openclaw-fortune.workers.dev/variant_metrics}"

echo "===== LP AUTOPILOT START ====="

./scripts/generated/run_lp_pattern_extractor_v1.sh || true
./scripts/generated/run_lp_critic_v1.sh || true
./scripts/generated/run_lp_rewriter_v2.sh || true

cp -f data/lp_research/rewritten_love_lp_A.html deploy/fortune/pages/index_A.html 2>/dev/null || true
cp -f data/lp_research/rewritten_love_lp_B.html deploy/fortune/pages/index_B.html 2>/dev/null || true
cp -f data/lp_research/rewritten_love_lp_C.html deploy/fortune/pages/index_C.html 2>/dev/null || true

python3 - <<'PY'
from pathlib import Path
pages = Path("deploy/fortune/pages")
for name in ["index_A.html","index_B.html","index_C.html","index.html"]:
    p = pages / name
    if not p.exists():
        continue
    s = p.read_text(encoding="utf-8")
    s = s.replace('href="/fortune/order.html"', 'href="order.html"')
    s = s.replace('href="/web/fortune/order.html"', 'href="order.html"')
    p.write_text(s, encoding="utf-8")
print("autopilot_links_fixed")
PY

./scripts/generated/run_lp_variant_judge_v2.sh || true
./scripts/generated/run_lp_variant_metrics_v1.sh || true

cd deploy/fortune/pages || exit 1
wrangler pages deploy . --project-name openclaw-fortune

echo "===== LP AUTOPILOT DONE ====="
