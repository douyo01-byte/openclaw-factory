#!/bin/bash
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
set -a
[ -f env/telegram.env ] && source env/telegram.env
[ -f env/telegram_ceo.env ] && source env/telegram_ceo.env
[ -f env/telegram_daemon.env ] && source env/telegram_daemon.env
set +a
[ -x .venv/bin/python ] && PY=.venv/bin/python || PY=python3
exec "$PY" bots/secretary_llm_v1.py >> logs/secretary_llm_v1.launchd.out 2>> logs/secretary_llm_v1.launchd.err
