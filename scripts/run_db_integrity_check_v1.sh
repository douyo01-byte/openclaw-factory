#!/bin/bash
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export FACTORY_DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
set -a
[ -f env/telegram.env ] && source env/telegram.env
[ -f env/telegram_ceo.env ] && source env/telegram_ceo.env
[ -f env/telegram_daemon.env ] && source env/telegram_daemon.env
set +a
[ -x .venv/bin/python ] && PY=.venv/bin/python || PY=python3
exec "$PY" bots/db_integrity_check_v1.py >> logs/db_integrity_check_v1.launchd.out 2>> logs/db_integrity_check_v1.launchd.err
