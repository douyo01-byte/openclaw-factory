#!/bin/zsh
set -euo pipefail
msg="${1:-educate Bを分析して勝ち軸を3つ出して https://kuu-medic.com/products/educate-b}"
intent="$(printf '%s' "$msg" | python3 bots/conversation_intent_router_v1.py)"
context="$(printf '%s' "$msg" | python3 bots/conversation_context_resolver_v1.py)"
plan_payload="$(python3 - <<'PY' "$msg" "$intent" "$context"
import json,sys
text=sys.argv[1]
intent=json.loads(sys.argv[2])
context=json.loads(sys.argv[3])
print(json.dumps({"domain":intent["domain"],"text":text,"context":context}, ensure_ascii=False))
PY
)"
plan="$(printf '%s' "$plan_payload" | python3 bots/task_decomposer_v1.py)"
job_payload="$(python3 - <<'PY' "$plan"
import json,sys
plan=json.loads(sys.argv[1])
plan["source_chat_id"]="test_chat"
plan["source_message_id"]="test_msg_1"
plan["assigned_ai"]="Kaikun04"
print(json.dumps(plan, ensure_ascii=False))
PY
)"
printf '%s' "$job_payload" | python3 bots/conversation_job_store_v1.py
