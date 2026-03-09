#!/usr/bin/env bash
set -euo pipefail

cd ~/AI/openclaw-factory-daemon || exit 1

sqlite3 data/openclaw.db "
select status,count(*)
from dev_proposals
group by status;
"

launchctl list | grep openclaw
