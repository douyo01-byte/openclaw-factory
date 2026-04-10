#!/bin/bash
set -euo pipefail

URL="https://openclaw-fortune.pages.dev"

UA_LIST=(
"Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"
"Mozilla/5.0 (Linux; Android 13)"
"Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
)

for i in {1..50}
do
  UA=${UA_LIST[$((RANDOM % ${#UA_LIST[@]}))]}
  curl -s -A "$UA" "$URL" > /dev/null
  sleep $(awk -v min=0.5 -v max=2 'BEGIN{srand(); print min+rand()*(max-min)}')
done

echo "traffic_sent=50"
