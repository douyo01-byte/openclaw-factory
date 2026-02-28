#!/usr/bin/env bash
set -euo pipefail
tok="${1:?token}"
plist="$HOME/Library/LaunchAgents/openclaw.telegram.env.plist"
cat > "$plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key><string>openclaw.telegram.env</string>
    <key>ProgramArguments</key>
    <array><string>/bin/launchctl</string><string>setenv</string><string>TELEGRAM_BOT_TOKEN</string><string>${tok}</string></array>
    <key>RunAtLoad</key><true/>
  </dict>
</plist>
PLIST
launchctl unload "$plist" >/dev/null 2>&1 || true
launchctl load "$plist"
launchctl start openclaw.telegram.env || true
launchctl getenv TELEGRAM_BOT_TOKEN | head
