#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
source .venv/bin/activate || exit 1
export PYTHONPATH="$PWD"
export DB_PATH="$HOME/AI/openclaw-factory/data/openclaw.db"
export FACTORY_DB_PATH="$HOME/AI/openclaw-factory/data/openclaw.db"
mkdir -p logs

POLL_SLEEP_SECONDS="${TG_POLL_LOOP_SLEEP_SECONDS:-30}"
HEARTBEAT_EVERY_SECONDS="${TG_POLL_HEARTBEAT_EVERY_SECONDS:-300}"
ERROR_REPEAT_SECONDS="${TG_POLL_ERROR_REPEAT_SECONDS:-300}"
STATE_DIR="logs/.tg_poll_loop_state"
mkdir -p "$STATE_DIR"

now_epoch () {
  date '+%s'
}

step () {
  local msg="$1"
  local force="${2:-0}"
  local now last
  now="$(now_epoch)"
  last="$(cat "$STATE_DIR/heartbeat.last" 2>/dev/null || echo 0)"
  if [ "$force" = "1" ] || [ $((now - last)) -ge "$HEARTBEAT_EVERY_SECONDS" ]; then
    echo "[$(date '+%F %T')] $msg" >> logs/tg_poll_heartbeat.log
    printf '%s\n' "$now" > "$STATE_DIR/heartbeat.last"
  fi
}

should_log_error () {
  local name="$1"
  local file="$STATE_DIR/${name}.error.last"
  local now last
  now="$(now_epoch)"
  last="$(cat "$file" 2>/dev/null || echo 0)"
  if [ $((now - last)) -ge "$ERROR_REPEAT_SECONDS" ]; then
    printf '%s\n' "$now" > "$file"
    return 0
  fi
  return 1
}

is_noop_output () {
  local out="$1"
  [ -z "$out" ] && return 0
  [ -z "$(printf '%s\n' "$out" | grep -Ev '^(ingest_seen=0|Done\. applied=0|meeting_done=0|company_done=0|help_done=0|noise_skipped=0|report_done=0|explain_done=0)$' || true)" ]
}

run_step () {
  local name="$1"
  shift
  local tmp rc out
  tmp="$(mktemp "${TMPDIR:-/tmp}/tg_poll_${name}.XXXXXX")"
  if "$@" > "$tmp" 2>&1; then
    rc=0
  else
    rc=$?
  fi
  out="$(cat "$tmp" 2>/dev/null || true)"
  rm -f "$tmp"

  if [ "$rc" -ne 0 ]; then
    if should_log_error "$name"; then
      echo "[$(date '+%F %T')] ${name} failed rc=${rc} repeated errors suppressed for ${ERROR_REPEAT_SECONDS}s" >> logs/tg_poll.log
    fi
    step "${name} failed rc=${rc}" 1
    return 0
  fi

  if ! is_noop_output "$out"; then
    echo "[$(date '+%F %T')] ${name} completed with material output" >> logs/tg_poll.log
  fi
}

step "tg_poll_loop configured sleep=${POLL_SLEEP_SECONDS}s heartbeat_every=${HEARTBEAT_EVERY_SECONDS}s error_repeat=${ERROR_REPEAT_SECONDS}s" 1

while true; do
  step "loop alive"
  set -a
  source env/telegram_replies.env
  source env/telegram_report.env 2>/dev/null || true
  if [ -f "$HOME/AI/openclaw-factory/env/openai.env" ]; then
    set +e
    source "$HOME/AI/openclaw-factory/env/openai.env" 2>/dev/null
    set -e
  fi
  [ -n "${TELEGRAM_REPORT_BOT_TOKEN:-}" ] && export TELEGRAM_BOT_TOKEN="$TELEGRAM_REPORT_BOT_TOKEN"
  [ -n "${CEO_CHAT_ID:-}" ] && export TELEGRAM_CHAT_ID="$CEO_CHAT_ID"
  set +a

  run_step "ingest_telegram_replies" python -u bots/ingest_telegram_replies_v1.py
  run_step "ingest_spec_answers" .venv/bin/python -u bots/ingest_spec_answers_v1.py
  run_step "meeting_orchestrator" .venv/bin/python -u bots/meeting_orchestrator_v1.py
  run_step "company_dashboard" .venv/bin/python -u bots/company_dashboard_v1.py
  run_step "ceo_help" .venv/bin/python -u bots/ceo_help_v1.py
  run_step "ceo_noise_cleanup" .venv/bin/python -u bots/ceo_noise_cleanup_v1.py
  run_step "report_orchestrator" .venv/bin/python -u bots/report_orchestrator_v1.py
  run_step "explain_orchestrator" .venv/bin/python -u bots/explain_orchestrator_v1.py
  run_step "ceo_hub_sender" .venv/bin/python -u bots/ceo_hub_sender_v1.py

  sleep "$POLL_SLEEP_SECONDS"
done
