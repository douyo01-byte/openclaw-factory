#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
source .venv/bin/activate || exit 1
export PYTHONPATH="$PWD"
export DB_PATH="$HOME/AI/openclaw-factory-daemon/data/openclaw_real.db"
export FACTORY_DB_PATH="$HOME/AI/openclaw-factory-daemon/data/openclaw_real.db"
mkdir -p logs

step () {
  echo "[$(date '+%F %T')] $1" >> logs/tg_poll_heartbeat.log
}

while true; do
  step "loop start"
  set -a
  source env/telegram_replies.env
  source env/telegram_report.env 2>/dev/null || true
  source "$HOME/AI/openclaw-factory/env/openai.env" 2>/dev/null || true
  [ -n "${TELEGRAM_REPORT_BOT_TOKEN:-}" ] && export TELEGRAM_BOT_TOKEN="$TELEGRAM_REPORT_BOT_TOKEN"
  [ -n "${CEO_CHAT_ID:-}" ] && export TELEGRAM_CHAT_ID="$CEO_CHAT_ID"
  set +a

  step "ingest_telegram_replies start"
  python -u bots/ingest_telegram_replies_v1.py >> logs/tg_poll.log 2>&1 || true
  step "ingest_telegram_replies end"

  step "ingest_spec_answers start"
  .venv/bin/python -u bots/ingest_spec_answers_v1.py >> logs/tg_poll.log 2>&1 || true
  step "ingest_spec_answers end"

  step "meeting_orchestrator start"
  .venv/bin/python -u bots/meeting_orchestrator_v1.py >> logs/tg_poll.log 2>&1 || true
  step "meeting_orchestrator end"

  step "company_dashboard start"
  .venv/bin/python -u bots/company_dashboard_v1.py >> logs/tg_poll.log 2>&1 || true
  step "company_dashboard end"

  step "ceo_help start"
  .venv/bin/python -u bots/ceo_help_v1.py >> logs/tg_poll.log 2>&1 || true
  step "ceo_help end"

  step "ceo_noise_cleanup start"
  .venv/bin/python -u bots/ceo_noise_cleanup_v1.py >> logs/tg_poll.log 2>&1 || true
  step "ceo_noise_cleanup end"

  step "report_orchestrator start"
  .venv/bin/python -u bots/report_orchestrator_v1.py >> logs/tg_poll.log 2>&1 || true
  step "report_orchestrator end"

  step "explain_orchestrator start"
  .venv/bin/python -u bots/explain_orchestrator_v1.py >> logs/tg_poll.log 2>&1 || true
  step "explain_orchestrator end"

  step "ceo_hub_sender start"
  .venv/bin/python -u bots/ceo_hub_sender_v1.py >> logs/tg_poll.log 2>&1 || true
  step "ceo_hub_sender end"


  step "loop end"
  sleep 2
done
