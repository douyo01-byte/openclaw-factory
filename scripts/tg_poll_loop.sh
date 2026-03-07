#!/bin/bash
set -euo pipefail
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
mkdir -p logs
exec </dev/null >> /Users/doyopc/AI/openclaw-factory-daemon/logs/tg_poll.log 2>> /Users/doyopc/AI/openclaw-factory-daemon/logs/tg_poll.err
source /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/activate || exit 1
export PYTHONUNBUFFERED=1
export PYTHONPATH=/Users/doyopc/AI/openclaw-factory-daemon
export DB_PATH=/Users/doyopc/AI/openclaw-factory-daemon/data/openclaw_real.db
export FACTORY_DB_PATH=/Users/doyopc/AI/openclaw-factory-daemon/data/openclaw_real.db

while true; do
  set -a
  source /Users/doyopc/AI/openclaw-factory-daemon/env/telegram_replies.env
  source /Users/doyopc/AI/openclaw-factory-daemon/env/telegram_report.env 2>/dev/null || true
  source /Users/doyopc/AI/openclaw-factory/env/openai.env 2>/dev/null || true
  [ -n "${TELEGRAM_REPORT_BOT_TOKEN:-}" ] && export TELEGRAM_BOT_TOKEN="$TELEGRAM_REPORT_BOT_TOKEN"
  [ -n "${CEO_CHAT_ID:-}" ] && export TELEGRAM_CHAT_ID="$CEO_CHAT_ID"
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

  echo "[$(date '+%F %T')] bots/report_orchestrator_v1.py"
  python -u bots/report_orchestrator_v1.py || true

  echo "[$(date '+%F %T')] bots/explain_orchestrator_v1.py"
  python -u bots/explain_orchestrator_v1.py || true

  echo "[$(date '+%F %T')] bots/ceo_hub_sender_v1.py"
  python -u bots/ceo_hub_sender_v1.py || true

  sleep 2
done
