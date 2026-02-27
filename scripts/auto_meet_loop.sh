#!/usr/bin/env bash
cd "$(cd "$(dirname "$0")" && pwd)/.."
set -euo pipefail

DB="${DB:-data/openclaw.db}"
INTERVAL_SEC="${INTERVAL_SEC:-600}"
TRAIN_LIMIT="${TRAIN_LIMIT:-50}"
CHAT_LIMIT="${CHAT_LIMIT:-200}"
ENRICH_LIMIT="${ENRICH_LIMIT:-200}"
SCORE_MIN="${SCORE_MIN:-70}"
CONTACTS_HEURISTIC_FILL="${CONTACTS_HEURISTIC_FILL:-1}"
AUTO_NO_CONTACTS_ZERO="${AUTO_NO_CONTACTS_ZERO:-1}"
NO_REQUIRE_REAL_CONTACTS="${NO_REQUIRE_REAL_CONTACTS:-1}"
NO_MIN_AGE_MIN="${NO_MIN_AGE_MIN:-180}"

mkdir -p logs
export DB_PATH="$DB"

while true; do
  echo "$(date +%F_%T) auto_meet_loop START" >> logs/heartbeat.log
  FEEDS_FILE=config/feeds/sakura.txt CORE_FEEDS_FILE=config/feeds/core.txt .venv/bin/python -m bots.team.sakura_scout --db "$DB" --role all --limit "$TRAIN_LIMIT" </dev/null >/dev/null 2>&1 || true
  DB="$DB" SCORE_MIN="$SCORE_MIN" CONTACTS_HEURISTIC_FILL="$CONTACTS_HEURISTIC_FILL" AUTO_NO_CONTACTS_ZERO="$AUTO_NO_CONTACTS_ZERO" NO_REQUIRE_REAL_CONTACTS="$NO_REQUIRE_REAL_CONTACTS" NO_MIN_AGE_MIN="$NO_MIN_AGE_MIN" CORE_PERSONA_FILE=config/personas/core.txt PERSONA_FILE=config/personas/kenji.txt .venv/bin/python -m bots.team.kenji_researcher --db "$DB" --limit "$CHAT_LIMIT" </dev/null >/dev/null 2>&1 || true
  CORE_PERSONA_FILE=config/personas/core.txt PERSONA_FILE=config/personas/miho.txt .venv/bin/python -m bots.team.miho_finder </dev/null >/dev/null 2>&1 || true
  .venv/bin/python -m bots.enrich_contacts_v1 --db "$DB" --limit "$ENRICH_LIMIT" </dev/null >/dev/null 2>&1 || true
  CORE_PERSONA_FILE=config/personas/core.txt PERSONA_FILE=config/personas/daiki.txt .venv/bin/python -m bots.team.daiki_analyst </dev/null >/dev/null 2>&1 || true
  CORE_PERSONA_FILE=config/personas/core.txt PERSONA_FILE=config/personas/aya.txt .venv/bin/python -m bots.team.aya_judge </dev/null >/dev/null 2>&1 || true
  .venv/bin/python -m bots.build_decision_patterns </dev/null >/dev/null 2>&1 || true
scripts/meeting_once.sh </dev/null >/dev/null 2>&1 || true
  echo "$(date +%F_%T) auto_meet_loop OK" >> logs/heartbeat.log
done
