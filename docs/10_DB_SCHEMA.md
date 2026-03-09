# OpenClaw DB Schema Notes

自動生成。手修正しない。

- branch: `dev/self-watch-recovery`
- db: `/Users/doyopc/AI/openclaw-factory-daemon/data/openclaw_real.db`

## table list
- ai_employees
- ceo_hub_events
- ceo_hub_events_old_20260308_1
- decision_patterns
- decisions
- decisions_old_20260306_095604
- dev_events
- dev_execution_log
- dev_proposals
- explain_sent
- inbox_commands
- kv
- proposal_conversation
- proposal_state
- reflection_requests
- report_sent
- retrospectives
- sent_questions
- sqlite_sequence
- tg_command_log
- tg_ingest_state
- tg_kv
- tg_private_chat_log
- tg_prompt_map

## current counts
- dev_proposals: 872
- proposal_state: 68
- proposal_conversation: 13481
- inbox_commands: 475
- decisions: 3
- ceo_hub_events: 290

## proposal_state status counts
- closed: 2
- merged: 61
- pr_created: 1
- refined: 4

## ceo_hub_events event counts
- ai_employee: 6
- learning_result: 79
- merged: 125
- pr_created: 75
- revenue: 5

## columns
### ai_employees
- id | INTEGER | notnull=0 | pk=1 | default=None
- employee_key | TEXT | notnull=1 | pk=0 | default=None
- display_name | TEXT | notnull=1 | pk=0 | default=None
- role_name | TEXT | notnull=1 | pk=0 | default=None
- mission | TEXT | notnull=1 | pk=0 | default=None
- is_enabled | INTEGER | notnull=1 | pk=0 | default=1
- created_at | TEXT | notnull=1 | pk=0 | default=datetime('now')

### ceo_hub_events
- id | INTEGER | notnull=0 | pk=1 | default=None
- event_type | TEXT | notnull=0 | pk=0 | default=None
- title | TEXT | notnull=0 | pk=0 | default=None
- body | TEXT | notnull=0 | pk=0 | default=None
- proposal_id | INTEGER | notnull=0 | pk=0 | default=None
- pr_url | TEXT | notnull=0 | pk=0 | default=None
- created_at | TEXT | notnull=0 | pk=0 | default=datetime('now')
- sent_at | TEXT | notnull=0 | pk=0 | default=None

### ceo_hub_events_old_20260308_1
- id | INTEGER | notnull=0 | pk=1 | default=None
- source | TEXT | notnull=1 | pk=0 | default=None
- source_key | TEXT | notnull=1 | pk=0 | default=None
- title | TEXT | notnull=1 | pk=0 | default=None
- body | TEXT | notnull=1 | pk=0 | default=None
- level | TEXT | notnull=1 | pk=0 | default='info'
- created_at | TEXT | notnull=1 | pk=0 | default=datetime('now')
- sent_at | TEXT | notnull=0 | pk=0 | default=None

### decision_patterns
- token | TEXT | notnull=0 | pk=1 | default=None
- weight | REAL | notnull=1 | pk=0 | default=None
- updated_at | TEXT | notnull=0 | pk=0 | default=datetime('now')

### decisions
- id | INTEGER | notnull=0 | pk=1 | default=None
- run_id | TEXT | notnull=0 | pk=0 | default=None
- target | TEXT | notnull=0 | pk=0 | default=None
- decision | TEXT | notnull=1 | pk=0 | default=None
- reason | TEXT | notnull=0 | pk=0 | default=None
- meta_json | TEXT | notnull=0 | pk=0 | default=None
- created_at | TEXT | notnull=1 | pk=0 | default=datetime('now')

### decisions_old_20260306_095604
- id | INTEGER | notnull=0 | pk=1 | default=None
- run_id | TEXT | notnull=0 | pk=0 | default=None
- created_at | TEXT | notnull=0 | pk=0 | default=datetime('now')
- target | TEXT | notnull=0 | pk=0 | default=None
- meta_json | TEXT | notnull=0 | pk=0 | default=None

### dev_events
- id | INTEGER | notnull=0 | pk=1 | default=None
- proposal_id | INTEGER | notnull=1 | pk=0 | default=None
- event_type | TEXT | notnull=1 | pk=0 | default=None
- payload | TEXT | notnull=0 | pk=0 | default=None
- created_at | TEXT | notnull=0 | pk=0 | default=datetime('now')

### dev_execution_log
- id | INTEGER | notnull=0 | pk=1 | default=None
- proposal_id | INTEGER | notnull=0 | pk=0 | default=None
- status | TEXT | notnull=0 | pk=0 | default=None
- message | TEXT | notnull=0 | pk=0 | default=None
- created_at | datetime | notnull=0 | pk=0 | default=current_timestamp

### dev_proposals
- id | INTEGER | notnull=0 | pk=1 | default=None
- status | TEXT | notnull=0 | pk=0 | default=None
- dev_stage | TEXT | notnull=0 | pk=0 | default=None
- pr_status | TEXT | notnull=0 | pk=0 | default=None
- pr_number | INTEGER | notnull=0 | pk=0 | default=None
- pr_url | TEXT | notnull=0 | pk=0 | default=None
- title | TEXT | notnull=0 | pk=0 | default=None
- description | TEXT | notnull=0 | pk=0 | default=None
- branch_name | TEXT | notnull=0 | pk=0 | default=None
- dev_attempts | INTEGER | notnull=0 | pk=0 | default=0
- spec_stage | TEXT | notnull=0 | pk=0 | default=None
- created_at | TEXT | notnull=0 | pk=0 | default=None
- notified_at | TEXT | notnull=0 | pk=0 | default=None
- notified_msg_id | TEXT | notnull=0 | pk=0 | default=None
- spec | TEXT | notnull=0 | pk=0 | default=None
- decided_at | TEXT | notnull=0 | pk=0 | default=None
- decided_by | TEXT | notnull=0 | pk=0 | default=None
- decision_note | TEXT | notnull=0 | pk=0 | default=None
- risk_level | TEXT | notnull=0 | pk=0 | default='low'
- source_ai | TEXT | notnull=0 | pk=0 | default=None
- brain_type | TEXT | notnull=0 | pk=0 | default=None
- confidence | REAL | notnull=0 | pk=0 | default=None
- category | TEXT | notnull=0 | pk=0 | default=None
- priority | INTEGER | notnull=0 | pk=0 | default=0
- project_decision | TEXT | notnull=0 | pk=0 | default=''
- duplicate_of | INTEGER | notnull=0 | pk=0 | default=None
- guard_status | TEXT | notnull=0 | pk=0 | default='pending'
- guard_reason | TEXT | notnull=0 | pk=0 | default=None
- infra_status | TEXT | notnull=0 | pk=0 | default=''
- infra_note | TEXT | notnull=0 | pk=0 | default=None
- cluster_id | TEXT | notnull=0 | pk=0 | default=None
- cluster_role | TEXT | notnull=0 | pk=0 | default=''
- guard_level | TEXT | notnull=0 | pk=0 | default=''
- result_type | TEXT | notnull=0 | pk=0 | default=None
- result_score | REAL | notnull=0 | pk=0 | default=None
- result_note | TEXT | notnull=0 | pk=0 | default=None
- target_system | TEXT | notnull=0 | pk=0 | default=None
- improvement_type | TEXT | notnull=0 | pk=0 | default=None
- explain | TEXT | notnull=0 | pk=0 | default=None
- explain_stage | TEXT | notnull=0 | pk=0 | default=None
- quality_score | INTEGER | notnull=0 | pk=0 | default=0

### explain_sent
- k | TEXT | notnull=0 | pk=1 | default=None
- sent_at | TEXT | notnull=1 | pk=0 | default=datetime('now')

### inbox_commands
- id | INTEGER | notnull=0 | pk=1 | default=None
- status | TEXT | notnull=0 | pk=0 | default=None
- text | TEXT | notnull=0 | pk=0 | default=None
- created_at | TEXT | notnull=0 | pk=0 | default=datetime('now')
- processed | INTEGER | notnull=0 | pk=0 | default=0
- applied_at | TEXT | notnull=0 | pk=0 | default=None
- source | TEXT | notnull=0 | pk=0 | default=None
- update_id | INTEGER | notnull=0 | pk=0 | default=None
- chat_id | TEXT | notnull=0 | pk=0 | default=None
- user_id | TEXT | notnull=0 | pk=0 | default=None
- username | TEXT | notnull=0 | pk=0 | default=None
- error | TEXT | notnull=0 | pk=0 | default=None
- message_id | INTEGER | notnull=0 | pk=0 | default=None
- reply_to_message_id | INTEGER | notnull=0 | pk=0 | default=None
- from_username | TEXT | notnull=0 | pk=0 | default=None
- from_name | TEXT | notnull=0 | pk=0 | default=None
- received_at | TEXT | notnull=0 | pk=0 | default=None

### kv
- k | TEXT | notnull=0 | pk=1 | default=None
- v | TEXT | notnull=1 | pk=0 | default=None
- updated_at | TEXT | notnull=0 | pk=0 | default=None

### proposal_conversation
- id | INTEGER | notnull=0 | pk=1 | default=None
- proposal_id | INTEGER | notnull=0 | pk=0 | default=None
- role | TEXT | notnull=0 | pk=0 | default=None
- message | TEXT | notnull=0 | pk=0 | default=None
- created_at | datetime | notnull=0 | pk=0 | default=current_timestamp

### proposal_state
- proposal_id | INTEGER | notnull=0 | pk=1 | default=None
- stage | TEXT | notnull=0 | pk=0 | default=None
- pending_questions | TEXT | notnull=0 | pk=0 | default=None
- updated_at | datetime | notnull=0 | pk=0 | default=current_timestamp
- pending_question | TEXT | notnull=0 | pk=0 | default=None
- notified_at | TEXT | notnull=0 | pk=0 | default=None

### reflection_requests
- id | INTEGER | notnull=0 | pk=1 | default=None
- window_n | INTEGER | notnull=1 | pk=0 | default=50
- status | TEXT | notnull=1 | pk=0 | default='new'
- result | TEXT | notnull=0 | pk=0 | default=None
- error | TEXT | notnull=0 | pk=0 | default=None
- processed_at | TEXT | notnull=0 | pk=0 | default=None
- created_at | TEXT | notnull=1 | pk=0 | default=datetime('now')

### report_sent
- k | TEXT | notnull=0 | pk=1 | default=None
- sent_at | TEXT | notnull=1 | pk=0 | default=datetime('now')

### retrospectives
- id | INTEGER | notnull=0 | pk=1 | default=None
- chat_id | TEXT | notnull=0 | pk=0 | default=None
- from_username | TEXT | notnull=0 | pk=0 | default=None
- text | TEXT | notnull=1 | pk=0 | default=None
- created_at | TEXT | notnull=1 | pk=0 | default=datetime('now')

### sent_questions
- proposal_id | INTEGER | notnull=0 | pk=1 | default=None
- chat_id | TEXT | notnull=1 | pk=0 | default=None
- message_id | INTEGER | notnull=1 | pk=0 | default=None
- sent_at | TEXT | notnull=1 | pk=0 | default=datetime('now')

### sqlite_sequence
- name |  | notnull=0 | pk=0 | default=None
- seq |  | notnull=0 | pk=0 | default=None

### tg_command_log
- id | INTEGER | notnull=0 | pk=1 | default=None
- chat_id | TEXT | notnull=0 | pk=0 | default=None
- user_id | TEXT | notnull=0 | pk=0 | default=None
- text | TEXT | notnull=0 | pk=0 | default=None
- created_at | TEXT | notnull=0 | pk=0 | default=None

### tg_ingest_state
- id | INTEGER | notnull=0 | pk=1 | default=None
- last_update_id | INTEGER | notnull=1 | pk=0 | default=None

### tg_kv
- k | TEXT | notnull=0 | pk=1 | default=None
- v | TEXT | notnull=0 | pk=0 | default=None
- updated_at | TEXT | notnull=0 | pk=0 | default=None

### tg_private_chat_log
- id | INTEGER | notnull=0 | pk=1 | default=None
- message_id | INTEGER | notnull=0 | pk=0 | default=None
- chat_id | INTEGER | notnull=0 | pk=0 | default=None
- text | TEXT | notnull=0 | pk=0 | default=None
- created_at | datetime | notnull=0 | pk=0 | default=current_timestamp
- update_id | INTEGER | notnull=0 | pk=0 | default=None

### tg_prompt_map
- id | INTEGER | notnull=0 | pk=1 | default=None
- chat_id | TEXT | notnull=1 | pk=0 | default=None
- message_id | INTEGER | notnull=1 | pk=0 | default=None
- proposal_id | INTEGER | notnull=1 | pk=0 | default=None
- kind | TEXT | notnull=1 | pk=0 | default='spec_question'
- created_at | TEXT | notnull=1 | pk=0 | default=datetime('now')
