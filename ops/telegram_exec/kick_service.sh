#!/bin/bash
set -euo pipefail
svc="${1:-}"
[ -n "$svc" ] || { echo "missing service"; exit 1; }
u=$(id -u)
launchctl kickstart -k "gui/$u/$svc"
sleep 2
launchctl print "gui/$u/$svc" | egrep 'state =|pid =|last exit code ='
