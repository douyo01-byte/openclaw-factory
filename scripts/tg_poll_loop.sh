#!/bin/bash
set -euo pipefail
REPORT_EVERY=600
LAST_REPORT_TS=0
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
mkdir -p logs
exec </dev/null >> /Users/doyopc/AI/openclaw-factory-daemon/logs/tg_poll.log 2>> /Users/doyopc/AI/openclaw-factory-daemon/logs/tg_poll.err
source /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/activate || exit 1
export PYTHONUNBUFFERED=1
export PYTHONPATH=/Users/doyopc/AI/openclaw-factory-daemon
export DB_PATH=/Users/doyopc/AI/openclaw-factory-daemon/data/openclaw_real.db
export FACTORY_DB_PATH=/Users/doyopc/AI/openclaw-factory/data/openclaw.db

while true; do
  set -a
  source /Users/doyopc/AI/openclaw-factory-daemon/env/telegram_replies.env 2>/dev/null || true
  source /Users/doyopc/AI/openclaw-factory-daemon/env/telegram_report.env 2>/dev/null || true
  source /Users/doyopc/AI/openclaw-factory-daemon/env/telegram_routing.env 2>/dev/null || true
  source /Users/doyopc/AI/openclaw-factory/env/openai.env 2>/dev/null || true
  set +a

  echo "[$(date '+%F %T')] bots/ingest_telegram_replies_v1.py"
  python -u bots/ingest_telegram_replies_v1.py || true

  echo "[$(date '+%F %T')] bots/ingest_spec_answers_v1.py"
  python -u bots/ingest_spec_answers_v1.py || true

  echo "[$(date '+%F %T')] bots/meeting_orchestrator_v1.py"
  python -u bots/meeting_orchestrator_v1.py || true

  echo "[$(date '+%F %T')] bots/ceo_explain_trigger_v1.py"
  python -u bots/ceo_explain_trigger_v1.py || true

  echo "[$(date '+%F %T')] bots/company_dashboard_v1.py"
  python -u bots/company_dashboard_v1.py || true

  echo "[$(date '+%F %T')] bots/ceo_help_v1.py"
  python -u bots/ceo_help_v1.py || true

  echo "[$(date '+%F %T')] bots/ceo_noise_cleanup_v1.py"
  python -u bots/ceo_noise_cleanup_v1.py || true

  echo "[$(date '+%F %T')] bots/explain_orchestrator_v1.py"
  TELEGRAM_BOT_TOKEN="${TELEGRAM_DEV_BOT_TOKEN:-}" TELEGRAM_CHAT_ID="${TELEGRAM_DEV_CHAT_ID:-}" python -u bots/explain_orchestrator_v1.py || true
  now_ts=$(date +%s)
  if [ $((now_ts - LAST_REPORT_TS)) -ge "$REPORT_EVERY" ]; then
    echo "[$(date '+%F %T')] bots/report_orchestrator_v1.py"
    python -u bots/report_orchestrator_v1.py || true
    LAST_REPORT_TS=$now_ts
  fi

  sleep 2
done
