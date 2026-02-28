#!/usr/bin/env bash
set -euo pipefail
cd "${HOME}/AI/openclaw-factory"
db="data/openclaw.db"
sqlite3 "$db" -csv "select id,pr_url from dev_proposals where status='approved' and pr_url is not null and pr_url<>'';" \
| while IFS=, read -r id url; do
  n="$(echo "$url" | sed -n 's#.*/pull/\([0-9][0-9]*\).*#\1#p')"
  [ -z "$n" ] && continue
  st="$(gh pr view "$n" --json state --jq '.state' 2>/dev/null || echo "")"
  if [ "$st" = "MERGED" ]; then
    sqlite3 "$db" "update dev_proposals set dev_stage='executed' where id=$id;"
  fi
done
