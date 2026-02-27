#!/usr/bin/env bash
set -euo pipefail
DB="${DB:-data/openclaw.db}"
id="${1:?item_id}"

url="$(sqlite3 "$DB" "select url from items where id=$id;")"
[ -n "$url" ] || exit 1

host="$(python - <<PY
from urllib.parse import urlparse
u="$url"
p=urlparse(u if "://" in u else "https://"+u)
print(p.netloc.split("@")[-1].split(":")[0])
PY
)"

[ -n "$host" ] || exit 0

sqlite3 "$DB" "insert or ignore into contacts(item_url,email,domain,source) values('$url','info@$host','$host','heuristic');"
sqlite3 "$DB" "insert or ignore into contacts(item_url,email,domain,source) values('$url','support@$host','$host','heuristic');"
sqlite3 "$DB" "insert or ignore into contacts(item_url,email,domain,source) values('$url','hello@$host','$host','heuristic');"
sqlite3 "$DB" "insert or ignore into contacts(item_url,email,domain,source) values('$url','contact@$host','$host','heuristic');"
