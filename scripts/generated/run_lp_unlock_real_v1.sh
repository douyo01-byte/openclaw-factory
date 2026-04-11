#!/bin/bash
set -euo pipefail

ORDER_URL="https://openclaw-fortune-order.openclaw-fortune.workers.dev/order"
UNLOCK_URL="https://openclaw-fortune-order.openclaw-fortune.workers.dev/unlock"

for v in A B C
do
  for i in {1..5}
  do
    RESP=$(curl -s -X POST "$ORDER_URL" \
      -d "plan=簡易鑑定" \
      -d "customer_name=unlock_$RANDOM" \
      -d "birth_date=1990-01-01" \
      -d "birth_time=12:00" \
      -d "birth_place=$v" \
      -d "question=テストです" \
      -d "email=unlock_$RANDOM@example.com" \
      -d "variant=$v")

    ORDER_ID=$(printf '%s' "$RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin)["order_id"])')

    curl -s -X POST "$UNLOCK_URL" \
      -H "content-type: application/json" \
      -d "{\"order_id\": $ORDER_ID}" \
      > /dev/null

    sleep 0.2
  done
done

echo "real_unlock_sent=15"
