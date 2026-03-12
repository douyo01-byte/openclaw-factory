#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
set -euo pipefail

ROOT="/Users/doyopc/AI/openclaw-factory-daemon"
PL="$HOME/Library/LaunchAgents"
LOG="$ROOT/logs"
u="$(id -u)"

mkdir -p "$PL" "$LOG"

make_plist() {
  local base="$1"
  local runner="$ROOT/scripts/run_${base}.sh"
  local out="$LOG/${base}.launchd.out"
  local err="$LOG/${base}.launchd.err"

  [ -f "$runner" ] || return 0

  cat > "$PL/jp.openclaw.${base}.plist" <<EOP
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
<key>Label</key><string>jp.openclaw.${base}</string>
<key>ProgramArguments</key>
<array>
<string>${runner}</string>
</array>
<key>RunAtLoad</key><true/>
<key>KeepAlive</key><true/>
<key>StandardOutPath</key><string>${out}</string>
<key>StandardErrorPath</key><string>${err}</string>
</dict>
</plist>
EOP

  chmod 644 "$PL/jp.openclaw.${base}.plist"
  plutil -lint "$PL/jp.openclaw.${base}.plist" >/dev/null
}

fix_reflection_runners() {
  cat > "$ROOT/scripts/run_reflection_v1.sh" <<'EOR'
#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="$DB_PATH"
export FACTORY_DB_PATH="$DB_PATH"
export PYTHONPATH="/Users/doyopc/AI/openclaw-factory-daemon"
exec python -u -m bots.reflection_v1 --limit 50 >> logs/reflection_v1.out 2>> logs/reflection_v1.err
EOR

  cat > "$ROOT/scripts/run_reflection_worker_v1.sh" <<'EOR'
#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="$DB_PATH"
export FACTORY_DB_PATH="$DB_PATH"
export PYTHONPATH="/Users/doyopc/AI/openclaw-factory-daemon"
exec python -u -m bots.reflection_worker_v1 >> logs/reflection_worker_v1.out 2>> logs/reflection_worker_v1.err
EOR

  cat > "$ROOT/scripts/run_tg_send_reflection_v1.sh" <<'EOR'
#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1
set -a
source /Users/doyopc/AI/openclaw-factory/env/telegram_kaikun03.env 2>/dev/null || true
source /Users/doyopc/AI/openclaw-factory/env/telegram.env 2>/dev/null || true
source /Users/doyopc/AI/openclaw-factory/env/telegram_daemon.env 2>/dev/null || true
source /Users/doyopc/AI/openclaw-factory/env/telegram_report.env 2>/dev/null || true
set +a
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="$DB_PATH"
export FACTORY_DB_PATH="$DB_PATH"
export PYTHONPATH="/Users/doyopc/AI/openclaw-factory-daemon"
exec python -u -m bots.tg_send_reflection_v1 >> logs/tg_send_reflection_v1.out 2>> logs/tg_send_reflection_v1.err
EOR

  chmod +x "$ROOT/scripts/run_reflection_v1.sh" \
           "$ROOT/scripts/run_reflection_worker_v1.sh" \
           "$ROOT/scripts/run_tg_send_reflection_v1.sh"
}

fix_sync_runners() {
  for base in sync_execute_stage_v1 sync_executor_ready_v1 sync_pr_ready_v1; do
    [ -f "$ROOT/bots/${base}.py" ] || continue
    cat > "$ROOT/scripts/run_${base}.sh" <<EOR
#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="\$DB_PATH"
export FACTORY_DB_PATH="\$DB_PATH"
export PYTHONPATH="/Users/doyopc/AI/openclaw-factory-daemon"
exec python -u bots/${base}.py >> logs/${base}.out 2>> logs/${base}.err
EOR
    chmod +x "$ROOT/scripts/run_${base}.sh"
  done
}

bootstrap_one() {
  local base="$1"
  local plist="$PL/jp.openclaw.${base}.plist"
  [ -f "$plist" ] || return 0
  launchctl bootout "gui/$u/jp.openclaw.${base}" 2>/dev/null || true
  launchctl bootstrap "gui/$u" "$plist" 2>/dev/null || true
  launchctl enable "gui/$u/jp.openclaw.${base}" 2>/dev/null || true
  launchctl kickstart -k "gui/$u/jp.openclaw.${base}" 2>/dev/null || true
}

fix_reflection_runners
fix_sync_runners

for s in "$ROOT"/scripts/run_*.sh; do
  [ -f "$s" ] || continue
  base="$(basename "$s")"
  base="${base#run_}"
  base="${base%.sh}"
  make_plist "$base"
done

important=(
  reflection_v1
  reflection_worker_v1
  tg_send_reflection_v1
  innovation_engine_v1
  innovation_llm_engine_v1
  schema_guardian_v1
  proposal_builder_loop_v1
  proposal_ranking_v1
  proposal_auto_approve_v1
  dev_router_v1
  auto_execute_now_v1
  sync_execute_stage_v1
  sync_executor_ready_v1
  sync_pr_ready_v1
  dev_pr_creator_v1
  dev_pr_sync_v1
  dev_pr_watcher_v1
  dev_pr_automerge_v1
  dev_merge_notify_v1
)

for base in "${important[@]}"; do
  bootstrap_one "$base"
done

sleep 8

echo "===== status ====="
for base in "${important[@]}"; do
  printf '%s|' "$base"
  launchctl print "gui/$u/jp.openclaw.${base}" 2>/dev/null | awk -F'= ' '
    /state =/ {gsub(/^[ \t]+/,"",$2); st=$2}
    /pid =/ {gsub(/^[ \t]+/,"",$2); pid=$2}
    /last exit code =/ {gsub(/^[ \t]+/,"",$2); ec=$2}
    END{
      if(st=="") st="-"
      if(pid=="") pid="-"
      if(ec=="") ec="-"
      printf "state=%s|pid=%s|exit=%s\n", st, pid, ec
    }'
done

echo
echo "===== reflection err ====="
tail -n 20 "$ROOT/logs/reflection_v1.err" 2>/dev/null || true
echo
tail -n 20 "$ROOT/logs/reflection_worker_v1.err" 2>/dev/null || true
echo
tail -n 20 "$ROOT/logs/tg_send_reflection_v1.err" 2>/dev/null || true
