#!/usr/bin/env bash
set -euo pipefail

home="$HOME"
repo="$home/AI/openclaw-factory-daemon"
pldir="$home/Library/LaunchAgents"
db="$repo/data/openclaw.db"
py="$repo/.venv/bin/python"
u="$(id -u)"

mkdir -p "$pldir" "$repo/logs"

pl_poll="$pldir/jp.openclaw.tg_poll_mux_v2.plist"
pl_pong="$pldir/jp.openclaw.tg_ping_responder.plist"
pl_apply="$pldir/jp.openclaw.apply_spec_answers.plist"

launchctl bootout "gui/$u" "$pl_poll" 2>/dev/null || true
launchctl bootout "gui/$u" "$pl_pong" 2>/dev/null || true
launchctl bootout "gui/$u" "$pl_apply" 2>/dev/null || true

pkill -f 'tg_poll_mux_v2\.py|tg_ping_responder_loop_v1\.py|apply_spec_answers_loop_v1\.py' 2>/dev/null || true
rm -f /tmp/jp.openclaw.tg_poll_mux_v2.lock 2>/dev/null || true

cat > "$pl_poll" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>jp.openclaw.tg_poll_mux_v2</string>
  <key>WorkingDirectory</key><string>$repo</string>
  <key>EnvironmentVariables</key><dict>
    <key>DB_PATH</key><string>$db</string>
    <key>OCLAW_DB_PATH</key><string>$db</string>
    <key>OCLAW_TG_POLL_LOCK</key><string>/tmp/jp.openclaw.tg_poll_mux_v2.lock</string>
  </dict>
  <key>ProgramArguments</key><array>
    <string>$py</string><string>-u</string><string>bots/tg_poll_mux_v2.py</string>
  </array>
  <key>StandardOutPath</key><string>$repo/logs/tg_poll_mux_v2.out</string>
  <key>StandardErrorPath</key><string>$repo/logs/tg_poll_mux_v2.err</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
</dict></plist>
PLIST

cat > "$pl_pong" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>jp.openclaw.tg_ping_responder</string>
  <key>WorkingDirectory</key><string>$repo</string>
  <key>EnvironmentVariables</key><dict>
    <key>DB_PATH</key><string>$db</string>
    <key>OCLAW_DB_PATH</key><string>$db</string>
  </dict>
  <key>ProgramArguments</key><array>
    <string>$py</string><string>-u</string><string>bots/tg_ping_responder_loop_v1.py</string>
  </array>
  <key>StandardOutPath</key><string>$repo/logs/tg_ping_responder.out</string>
  <key>StandardErrorPath</key><string>$repo/logs/tg_ping_responder.err</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
</dict></plist>
PLIST

cat > "$pl_apply" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>jp.openclaw.apply_spec_answers</string>
  <key>WorkingDirectory</key><string>$repo</string>
  <key>EnvironmentVariables</key><dict>
    <key>DB_PATH</key><string>$db</string>
    <key>OCLAW_DB_PATH</key><string>$db</string>
  </dict>
  <key>ProgramArguments</key><array>
    <string>$py</string><string>-u</string><string>bots/apply_spec_answers_loop_v1.py</string>
  </array>
  <key>StandardOutPath</key><string>$repo/logs/apply_spec_answers.out</string>
  <key>StandardErrorPath</key><string>$repo/logs/apply_spec_answers.err</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
</dict></plist>
PLIST

chmod 644 "$pl_poll" "$pl_pong" "$pl_apply"
plutil -lint "$pl_poll" >/dev/null
plutil -lint "$pl_pong" >/dev/null
plutil -lint "$pl_apply" >/dev/null

launchctl bootstrap "gui/$u" "$pl_poll"
launchctl bootstrap "gui/$u" "$pl_pong"
launchctl bootstrap "gui/$u" "$pl_apply"
launchctl enable "gui/$u/jp.openclaw.tg_poll_mux_v2" 2>/dev/null || true
launchctl enable "gui/$u/jp.openclaw.tg_ping_responder" 2>/dev/null || true
launchctl enable "gui/$u/jp.openclaw.apply_spec_answers" 2>/dev/null || true
launchctl kickstart -k "gui/$u/jp.openclaw.tg_poll_mux_v2" 2>/dev/null || true
launchctl kickstart -k "gui/$u/jp.openclaw.tg_ping_responder" 2>/dev/null || true
launchctl kickstart -k "gui/$u/jp.openclaw.apply_spec_answers" 2>/dev/null || true

echo "OK: installed LaunchAgents (python direct)"
