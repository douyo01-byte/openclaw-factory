#!/bin/bash
set -euo pipefail

URL="https://openclaw-fortune.pages.dev"

for i in {1..20}
do
  curl -s "$URL" > /dev/null
  sleep 0.3
done

echo "traffic_sent=20"
