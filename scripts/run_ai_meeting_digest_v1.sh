#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/AI/openclaw-factory-daemon" || exit 1
source .venv/bin/activate || exit 1
set -a
source env/openai.env 2>/dev/null || true
source env/telegram.env 2>/dev/null || true
source env/telegram_daemon.env 2>/dev/null || true
source env/telegram_replies.env 2>/dev/null || true
source env/telegram_report.env 2>/dev/null || true
source env/telegram_routing.env 2>/dev/null || true
set +a
export DB_PATH="$HOME/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="$DB_PATH"
export PYTHONPATH="$HOME/AI/openclaw-factory-daemon"
export AI_MEETING_DIGEST_WINDOW_MIN="${AI_MEETING_DIGEST_WINDOW_MIN:-20}"
export AI_MEETING_DIGEST_MIN_MERGED="${AI_MEETING_DIGEST_MIN_MERGED:-2}"
export AI_MEETING_DIGEST_MIN_PR="${AI_MEETING_DIGEST_MIN_PR:-2}"
export AI_MEETING_DIGEST_MIN_LEARN="${AI_MEETING_DIGEST_MIN_LEARN:-2}"
export AI_MEETING_DIGEST_COOLDOWN_MIN="${AI_MEETING_DIGEST_COOLDOWN_MIN:-15}"
exec python -u bots/ai_meeting_digest_v1.py >> logs/ai_meeting_digest_v1.out 2>> logs/ai_meeting_digest_v1.err
