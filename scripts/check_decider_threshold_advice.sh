#!/bin/zsh
set -euo pipefail
cd ~/AI/openclaw-factory-daemon || exit 1
DB="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"

echo '===== decider threshold advice ====='
sqlite3 "$DB" "
select
  coalesce(source_ai,''),
  coalesce(decision,''),
  coalesce(matched_band,''),
  sample_count,
  round(avg_source_bias,4),
  round(avg_cluster_bias,4),
  coalesce(suggested_action,''),
  coalesce(suggestion_reason,'')
from decider_threshold_advice
order by sample_count desc, source_ai asc, decision asc, matched_band asc;
"


echo
echo '===== threshold advice action summary ====='
sqlite3 "$DB" "
select
  coalesce(suggested_action,'') as suggested_action,
  count(*) as cnt
from decider_threshold_advice
group by coalesce(suggested_action,'')
order by cnt desc, suggested_action asc;
"
