#!/bin/bash
set -euo pipefail
u=$(id -u)
for s in \
  jp.openclaw.private_reply_to_inbox_v1 \
  jp.openclaw.secretary_llm_v1 \
  jp.openclaw.task_router_v1 \
  jp.openclaw.ingest_private_replies_kaikun04 \
  jp.openclaw.kaikun04_router_worker_v1 \
  jp.openclaw.router_reply_finisher_v1 \
  jp.openclaw.telegram_ops_executor_v1
do
  echo "----- $s -----"
  launchctl print "gui/$u/$s" 2>/dev/null | egrep 'state =|pid =|last exit code =' || true
done
