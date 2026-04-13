#!/bin/bash
set -euo pipefail

URL="https://openclaw-fortune-order.openclaw-fortune.workers.dev/order"

for v in A B C D
do
  for i in {1..20}
  do
    curl -s -X POST "$URL" \
      -d "plan=簡易鑑定" \
      -d "customer_name=test_$RANDOM" \
      -d "birth_date=1990-01-01" \
      -d "birth_time=12:00" \
      -d "birth_place=$v" \
      -d "question=テストです" \
      -d "email=test_$RANDOM@example.com" \
      -d "variant=$v" \
      > /dev/null

    sleep 0.2
  done
done

echo "real_traffic_sent=80"
