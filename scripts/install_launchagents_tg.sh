#!/usr/bin/env bash
set -euo pipefail

home="$HOME"
repo="$home/AI/openclaw-factory-daemon"
pldir="$home/Library/LaunchAgents"
db="$repo/data/openclaw.db"
u="$(id -u)"

mkdir -p "$pldir" "$repo/logs"

pl_poll="$pldir/jp.openclaw.tg_poll_mux_v2.plist"
pl_pong="$pldir/jp.openclaw.tg_ping_responder.plist"

poll_cmd="cd \"${repo}\" && source .venv/bin/activate && set -a && source env/telegram_daemon.env && set +a && export DB_PATH=\"${db}\" && export OCLAW_DB_PATH=\"${db}\" && export OCLAW_TG_POLL_LOCK=\"/tmp/jp.openclaw.tg_poll_mux_v2.lock\" && sqlite3 \"${db}\" \"pragma journal_mode=WAL; pragma synchronous=NORMAL; pragma busy_timeout=8000;\" >/dev/null && python -u bots/tg_poll_mux_v2.py"
pong_cmd="cd \"${repo}\" && source .venv/bin/activate && set -a && source env/telegram_daemon.env && set +a && export DB_PATH=\"${db}\" && export OCLAW_DB_PATH=\"${db}\" && sqlite3 \"${db}\" \"pragma journal_mode=WAL; pragma synchronous=NORMAL; pragma busy_timeout=8000;\" >/dev/null && python -u bots/tg_ping_responder_loop_v1.py"

xml_escape() {
  printf '%s' "$1" | /usr/bin/sed \
    -e 's/&/\&amp;/g' \
    -e 's/</\&lt;/g' \
    -e 's/>/\&gt;/g' \
    -e 's/"/\&quot;/g' \
    -e "s/'/\&apos;/g"
}

poll_xml="$(xml_escape "$poll_cmd")"
pong_xml="$(xml_escape "$pong_cmd")"

cat > "$pl_poll" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>jp.openclaw.tg_poll_mux_v2</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>${repo}/logs/tg_poll_mux_v2.out</string>
  <key>StandardErrorPath</key><string>${repo}/logs/tg_poll_mux_v2.err</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-lc</string>
    <string>${poll_xml}</string>
  </array>
</dict>
</plist>
PLIST

cat > "$pl_pong" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>jp.openclaw.tg_ping_responder</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>${repo}/logs/tg_ping_responder.out</string>
  <key>StandardErrorPath</key><string>${repo}/logs/tg_ping_responder.err</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-lc</string>
    <string>${pong_xml}</string>
  </array>
</dict>
</plist>
PLIST

chmod 644 "$pl_poll" "$pl_pong"
plutil -lint "$pl_poll" >/dev/null
plutil -lint "$pl_pong" >/dev/null

launchctl bootout "gui/$u" "$pl_poll" 2>/dev/null || true
launchctl bootout "gui/$u" "$pl_pong" 2>/dev/null || true
rm -f "/tmp/jp.openclaw.tg_poll_mux_v2.lock" 2>/dev/null || true

launchctl bootstrap "gui/$u" "$pl_poll"
launchctl bootstrap "gui/$u" "$pl_pong"
launchctl enable "gui/$u/jp.openclaw.tg_poll_mux_v2" 2>/dev/null || true
launchctl enable "gui/$u/jp.openclaw.tg_ping_responder" 2>/dev/null || true
launchctl kickstart -k "gui/$u/jp.openclaw.tg_poll_mux_v2" 2>/dev/null || true
launchctl kickstart -k "gui/$u/jp.openclaw.tg_ping_responder" 2>/dev/null || true

echo "OK: installed LaunchAgents"
