#!/bin/bash
set -euo pipefail
cd "$HOME/AI/openclaw-factory-daemon" || exit 1

DAY="$(date +%Y%m%d)"
ARCH="archive/logs/$DAY"
mkdir -p "$ARCH"

keep='^(tg_poll\.log|tg_poll_heartbeat\.log|spec_refiner_v2\.out|spec_refiner_v2\.err|spec_notify_v1\.out|spec_notify_v1\.err|jp\.openclaw\.dev_pr_watcher_v1\.out|jp\.openclaw\.dev_pr_watcher_v1\.err|dev_executor_daemon_v1\.out|dev_executor_daemon_v1\.err|dev_command_executor_v1\.out|dev_command_executor_v1\.err|tg_private_ingest_v1\.out|tg_private_ingest_v1\.err|self_healing_v2\.log|self_healing_v1\.log|dev_executor_daemon\.log|log_policy_snapshot\.txt)$'

move_if_needed() {
  f="$1"
  b="$(basename "$f")"
  [ -f "$f" ] || return 0
  echo "$b" | egrep -q "$keep" && return 0

  size=$(stat -f%z "$f" 2>/dev/null || echo 0)
  old=0
  find "$f" -mtime +1 -print -quit 2>/dev/null | grep -q . && old=1

  if [ "$size" -gt 1048576 ] || [ "$old" -eq 1 ]; then
    mv "$f" "$ARCH/$b"
    printf '%s MOVE %s -> %s\n' "$(date '+%F %T')" "$f" "$ARCH/$b" >> logs/log_rotate_safe.log
  fi
}

find logs -maxdepth 1 -type f \( -name '*.out' -o -name '*.err' -o -name '*.log' -o -name '*.txt' \) | while read -r f
do
  move_if_needed "$f"
done
