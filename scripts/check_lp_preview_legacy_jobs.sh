#!/bin/bash
set -euo pipefail
export DB_PATH="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"
sqlite3 "$DB_PATH" "
select
  j.id,
  j.current_phase,
  j.status,
  max(case when a.artifact_type='lp_html_export_v3' then 1 else 0 end) as has_v3,
  max(case when a.artifact_type='lp_html_export' then 1 else 0 end) as has_generic,
  max(case when a.artifact_type='public_preview_url' then 1 else 0 end) as has_preview
from conversation_jobs j
left join conversation_artifacts a on a.job_id=j.id
group by j.id
having has_preview=1 and has_v3=0
order by j.id asc;
"
