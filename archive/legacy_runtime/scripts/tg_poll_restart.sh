#!/usr/bin/env bash
set -euo pipefail

# kill any stray pollers (manual runs etc.)
pkill -f "bots.tg_inbox_poll_daemon_v1" 2>/dev/null || true
pkill -f "tg_inbox_poll" 2>/dev/null || true
pkill -f "getUpdates" 2>/dev/null || true

launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/jp.kuu.openclaw.tg_poll.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/jp.kuu.openclaw.tg_poll.plist
launchctl kickstart -k gui/$(id -u)/jp.kuu.openclaw.tg_poll

sleep 1
launchctl print gui/$(id -u)/jp.kuu.openclaw.tg_poll | egrep -n "state|runs|pid|last exit code" || true
tail -n 30 ~/Library/Logs/openclaw/tg_poll.err.log || true
