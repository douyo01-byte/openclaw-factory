#!/bin/bash
cd ~/AI/openclaw-factory-daemon || exit 1
echo "=== DB ==="
sqlite3 ../openclaw-factory/data/openclaw.db "select count(*) from dev_proposals;"
sqlite3 ../openclaw-factory/data/openclaw.db "select count(*) from ceo_hub_events;"
echo "=== AGENTS ==="
launchctl list | grep jp.openclaw
