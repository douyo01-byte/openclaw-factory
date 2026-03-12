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
  local plist="$PL/jp.openclaw.${base}.plist"
  [ -f "$runner" ] || return 0

  cat > "$plist" <<EOP
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
<key>StandardOutPath</key><string>${LOG}/${base}.launchd.out</string>
<key>StandardErrorPath</key><string>${LOG}/${base}.launchd.err</string>
</dict>
</plist>
EOP
  chmod 644 "$plist"
  plutil -lint "$plist" >/dev/null
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

for s in "$ROOT"/scripts/run_*.sh; do
  [ -f "$s" ] || continue
  base="$(basename "$s")"
  base="${base#run_}"
  base="${base%.sh}"
  make_plist "$base"
done

skip_re='^(run_py|run_daemon|run_business_engine|run_revenue_engine|run_innovation_engine|run_learning_pattern_engine|run_mainstream_supply|run_ops_supply_engine)\.sh$'

for s in "$ROOT"/scripts/run_*.sh; do
  [ -f "$s" ] || continue
  bn="$(basename "$s")"
  if echo "$bn" | egrep -q "$skip_re"; then
    continue
  fi
  base="${bn#run_}"
  base="${base%.sh}"
  bootstrap_one "$base"
done

sleep 8

echo "===== connected summary ====="
for p in "$PL"/jp.openclaw*.plist; do
  [ -f "$p" ] || continue
  base="$(basename "$p")"
  base="${base#jp.openclaw.}"
  base="${base%.plist}"
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
done | sort

echo
echo "===== missing runner targets from plist ====="
python3 - <<'PY'
from pathlib import Path
import re
pl = Path.home() / "Library/LaunchAgents"
for p in sorted(pl.glob("jp.openclaw*.plist")):
    txt = p.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"<string>(/Users/doyopc/AI/openclaw-factory-daemon/scripts/[^<]+)</string>", txt)
    if m:
        prog = Path(m.group(1))
        if not prog.exists():
            print(f"{p.name}|missing_program={prog}")
PY

echo
echo "===== key services ====="
for base in \
innovation_engine_v1 \
innovation_llm_engine_v1 \
schema_guardian_v1 \
proposal_builder_loop_v1 \
proposal_ranking_v1 \
proposal_auto_approve_v1 \
dev_router_v1 \
auto_execute_now_v1 \
sync_execute_stage_v1 \
sync_executor_ready_v1 \
sync_pr_ready_v1 \
dev_pr_creator_v1 \
dev_pr_sync_v1 \
dev_pr_watcher_v1 \
dev_pr_automerge_v1 \
dev_merge_notify_v1 \
reflection_v1 \
reflection_worker_v1 \
tg_send_reflection_v1
do
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
