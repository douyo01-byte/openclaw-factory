#!/bin/zsh
set -euo pipefail
msg="${1:-educate Bを分析して勝ち軸を3つ出して https://kuu-medic.com/products/educate-b}"
intent="$(printf '%s' "$msg" | python3 bots/conversation_intent_router_v1.py)"
context="$(printf '%s' "$msg" | python3 bots/conversation_context_resolver_v1.py)"
payload="$(python3 - <<'PY' "$msg" "$intent" "$context"
import json,sys
text=sys.argv[1]
intent=json.loads(sys.argv[2])
context=json.loads(sys.argv[3])
print(json.dumps({"domain":intent["domain"],"text":text,"context":context}, ensure_ascii=False))
PY
)"
plan="$(printf '%s' "$payload" | python3 bots/task_decomposer_v1.py)"
printf '%s' "$plan" | python3 bots/telegram_reply_formatter_v1.py
