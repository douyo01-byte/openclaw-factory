# OpenClaw DB Schema

## dev_proposals
- id | INTEGER
- status | TEXT
- dev_stage | TEXT
- pr_status | TEXT
- pr_number | INTEGER
- pr_url | TEXT
- title | TEXT
- description | TEXT
- branch_name | TEXT
- dev_attempts | INTEGER
- spec_stage | TEXT
- created_at | TEXT
- notified_at | TEXT
- notified_msg_id | TEXT
- spec | TEXT
- decided_at | TEXT
- decided_by | TEXT
- decision_note | TEXT
- risk_level | TEXT
- source_ai | TEXT
- brain_type | TEXT
- confidence | REAL
- category | TEXT
- priority | INTEGER
- project_decision | TEXT
- duplicate_of | INTEGER
- guard_status | TEXT
- guard_reason | TEXT
- infra_status | TEXT
- infra_note | TEXT
- cluster_id | TEXT
- cluster_role | TEXT
- guard_level | TEXT
- result_type | TEXT
- result_score | REAL
- result_note | TEXT
- target_system | TEXT
- improvement_type | TEXT
- explain | TEXT
- explain_stage | TEXT
- quality_score | INTEGER
- source | TEXT

## ceo_hub_events
- id | INTEGER
- event_type | TEXT
- title | TEXT
- body | TEXT
- proposal_id | INTEGER
- pr_url | TEXT
- created_at | TEXT
- sent_at | TEXT

## inbox_commands
- id | INTEGER
- status | TEXT
- text | TEXT
- created_at | TEXT
- processed | INTEGER
- applied_at | TEXT
- source | TEXT
- update_id | INTEGER
- chat_id | TEXT
- user_id | TEXT
- username | TEXT
- error | TEXT
- message_id | INTEGER
- reply_to_message_id | INTEGER
- from_username | TEXT
- from_name | TEXT
- received_at | TEXT

## sqlite_sequence
- name | 
- seq | 

## kv
- k | TEXT
- v | TEXT
- updated_at | TEXT

## proposal_state
- proposal_id | INTEGER
- stage | TEXT
- pending_questions | TEXT
- updated_at | TEXT
- pending_question | TEXT

## proposal_conversation
- id | INTEGER
- proposal_id | INTEGER
- role | TEXT
- message | TEXT
- created_at | TEXT

## tg_prompt_map
- id | INTEGER
- chat_id | TEXT
- message_id | INTEGER
- proposal_id | INTEGER
- kind | TEXT
- created_at | TEXT

## tg_kv
- k | TEXT
- v | TEXT

## tg_private_chat_log
- id | INTEGER
- update_id | INTEGER
- message_id | INTEGER
- chat_id | INTEGER
- text | TEXT
- created_at | TEXT

## decisions
- id | INTEGER
- run_id | TEXT
- target | TEXT
- decision | TEXT
- reason | TEXT
- meta_json | TEXT
- created_at | TEXT

## dev_events
- id | INTEGER
- proposal_id | INTEGER
- event_type | TEXT
- payload | TEXT
- created_at | TEXT

## system_metrics
- key | TEXT
- value | REAL
- updated_at | datetime

## company_orders
- id | INTEGER
- order_text | TEXT
- priority | INTEGER
- status | TEXT
- created_at | datetime

## learning_results
- id | INTEGER
- experiment | TEXT
- change_value | TEXT
- result_score | REAL
- created_at | datetime

