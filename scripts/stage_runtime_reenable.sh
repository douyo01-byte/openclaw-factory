#!/bin/bash
set -euo pipefail

DB="${DB_PATH:-/Users/doyopc/AI/openclaw-factory/data/openclaw.db}"
UIDX="$(id -u)"

health() {
  echo '===== HEALTH ====='
  sqlite3 "$DB" "
select count(distinct pr_url)
from dev_proposals
where coalesce(pr_status,'')='open'
  and coalesce(pr_url,'')<>'';
"
  sqlite3 "$DB" "
select
  coalesce(source_ai,''), count(distinct pr_url)
from dev_proposals
where coalesce(pr_status,'')='open'
  and coalesce(pr_url,'')<>''
group by 1
order by 2 desc;
"
  sqlite3 "$DB" "
select count(*)
from (
  select pr_url
  from dev_proposals
  where coalesce(pr_status,'')='open'
    and coalesce(pr_url,'')<>''
  group by pr_url
  having count(*) > 1
);
"
}

start_one() {
  local label="$1"
  launchctl bootout "gui/$UIDX/$label" 2>/dev/null || true
  launchctl bootstrap "gui/$UIDX" "$HOME/Library/LaunchAgents/$label.plist"
  launchctl enable "gui/$UIDX/$label" 2>/dev/null || true
  launchctl kickstart -k "gui/$UIDX/$label"
  sleep 15
  launchctl print "gui/$UIDX/$label" | egrep 'state =|pid =|last exit code =' || true
  health
}

echo '===== MINIMUM ====='
for lb in \
  jp.openclaw.open_pr_guard_v1 \
  jp.openclaw.dev_pr_watcher_v1 \
  jp.openclaw.dev_pr_creator_v1
do
  launchctl print "gui/$UIDX/$lb" | egrep 'state =|pid =|last exit code =' || true
done

health

echo '===== START proposal_promoter_v1 ====='
start_one jp.openclaw.proposal_promoter_v1

echo '===== START spec_refiner_v2 ====='
start_one jp.openclaw.spec_refiner_v2

echo '===== START spec_decomposer_v1 ====='
start_one jp.openclaw.spec_decomposer_v1

echo '===== FINAL ====='
health
