#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.." || exit 1
DB=data/openclaw.db

sqlite3 "$DB" "
delete from decision_patterns;

insert into decision_patterns(token,weight)
select dev_stage,count(*)
from dev_proposals
group by dev_stage;
"
