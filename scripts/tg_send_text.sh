#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
import sys,requests,plistlib,pathlib

plist=pathlib.Path.home()/"Library/LaunchAgents/jp.kuu.openclaw.tg_poll.plist"
env=plistlib.loads(plist.read_bytes())["EnvironmentVariables"]
token=env["TELEGRAM_BOT_TOKEN"]
chat_id=env["OCLAW_TELEGRAM_CHAT_ID"]

msg=sys.stdin.read().strip()
if not msg:
    raise SystemExit(0)

requests.post(
    f"https://api.telegram.org/bot{token}/sendMessage",
    json={"chat_id":chat_id,"text":msg}
).raise_for_status()

print("Done. sent=1")
PY
