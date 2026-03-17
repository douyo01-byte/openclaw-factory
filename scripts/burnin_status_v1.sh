#!/bin/bash
set -euo pipefail

echo "===== PRE-BURNIN CLEANUP ====="
./scripts/pre_burnin_cleanup_v1.sh || true
echo

echo "===== FINAL SANITY ====="
OCLAW_SKIP_SMOKE=1 ./scripts/run_final_sanity_v1.sh
echo

echo "===== ROUTER COUNTS ====="
sqlite3 -cmd ".headers on" -cmd ".mode column" /Users/doyopc/AI/openclaw-factory/data/openclaw.db "
select
  coalesce(target_bot,'') as target_bot,
  coalesce(status,'') as status,
  count(*) as cnt
from router_tasks
group by 1,2
order by 1,2;
"
echo

echo "===== OPEN PR ====="
sqlite3 -cmd ".headers on" -cmd ".mode column" /Users/doyopc/AI/openclaw-factory/data/openclaw.db "
select count(*) as open_pr
from dev_proposals
where coalesce(pr_status,'')='open'
  and coalesce(pr_url,'')<>'';
"
echo

echo "===== ACTIVE LAUNCHAGENTS ====="
uid=$(id -u)
for lb in \
  jp.openclaw.task_router_v1 \
  jp.openclaw.kaikun02_router_worker_v1 \
  jp.openclaw.kaikun04_router_worker_v1 \
  jp.openclaw.router_reply_finisher_v1 \
  jp.openclaw.private_reply_to_inbox_v1 \
  jp.openclaw.ingest_private_replies_kaikun02 \
  jp.openclaw.ingest_private_replies_kaikun04 \
  jp.openclaw.proposal_promoter_v1 \
  jp.openclaw.spec_refiner_v2 \
  jp.openclaw.spec_decomposer_v1 \
  jp.openclaw.dev_pr_creator_v1 \
  jp.openclaw.dev_pr_watcher_v1 \
  jp.openclaw.innovation_llm_engine_v1 \
  jp.openclaw.db_lock_watchdog_v1 \
  jp.openclaw.router_stall_watchdog_v1 \
  jp.openclaw.pr_stall_watchdog_v1
do
  echo "--- $lb"
  launchctl print "gui/$uid/$lb" 2>/dev/null | egrep 'state =|pid =|last exit code =' || echo "missing"
done
