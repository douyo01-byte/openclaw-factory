#!/bin/bash
set -e

ROOT="/Users/doyopc/AI/openclaw-factory-daemon"
LOG="$ROOT/logs"
SCRIPTS="$ROOT/scripts"
LAUNCH="$HOME/Library/LaunchAgents"

bots=(
chat_research_v1
db_integrity_watchdog_v1
dev_proposal_notify_v1
market_brain_v1
parse_dev_reply_v1
pr_kicker_v1
revenue_brain_v1
scout_market_v2
self_evolution_engine_v1
watcher_kicker_v1
)

for b in "${bots[@]}"; do

cat > "$SCRIPTS/run_${b}.sh" <<EOT
#!/bin/bash
cd $ROOT
source .venv/bin/activate

set -a
[ -f env/openai.env ] && source env/openai.env
[ -f env/telegram.env ] && source env/telegram.env
set +a

export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="\$DB_PATH"
export FACTORY_DB_PATH="\$DB_PATH"
export PYTHONPATH="$ROOT"

exec python -u -m bots.${b} >> logs/${b}.out 2>> logs/${b}.err
EOT

chmod +x "$SCRIPTS/run_${b}.sh"

cat > "$LAUNCH/jp.openclaw.${b}.plist" <<EOT
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
"http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
<key>Label</key>
<string>jp.openclaw.${b}</string>

<key>ProgramArguments</key>
<array>
<string>$SCRIPTS/run_${b}.sh</string>
</array>

<key>RunAtLoad</key>
<true/>

<key>KeepAlive</key>
<true/>

<key>StandardOutPath</key>
<string>$LOG/${b}.launchd.out</string>

<key>StandardErrorPath</key>
<string>$LOG/${b}.launchd.err</string>

</dict>
</plist>
EOT

done
