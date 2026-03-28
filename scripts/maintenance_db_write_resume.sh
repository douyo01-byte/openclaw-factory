#!/bin/bash
set -euo pipefail
u=$(id -u)
PLIST_DIR="$HOME/Library/LaunchAgents"

TARGETS=(
  jp.openclaw.tg_poll_loop
  jp.openclaw.private_reply_to_inbox_v1
  jp.openclaw.router_reply_finisher_v1
  jp.openclaw.telegram_os_outbox_sender_v1
  jp.openclaw.self_improvement_to_learning_v1
  jp.openclaw.self_improvement_pattern_bridge_v1
  jp.openclaw.self_improvement_feedback_metrics_v1
  jp.openclaw.ingest_private_replies_kaikun04
  jp.openclaw.telegram_ops_executor_v1
  jp.openclaw.kaikun04_router_worker_v1
  jp.openclaw.telegram_os_creative_pipeline_v1
)

for t in "${TARGETS[@]}"; do
  launchctl bootstrap "gui/$u" "$PLIST_DIR/$t.plist" 2>/dev/null || true
done

sleep 2
launchctl list | grep '^.*jp\.openclaw\.' | sort
