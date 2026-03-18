# OpenClaw DB Schema

- generated_at: 2026-03-18T12:39:53.246220+00:00
- canonical_db: /Users/doyopc/AI/openclaw-factory/data/openclaw.db

## ai_employee_rankings
- rank_no | INTEGER
- source_ai | TEXT
- total_count | INTEGER
- merged_count | INTEGER
- merge_rate | REAL
- score | REAL
- updated_at | TEXT

## ai_employee_scores
- source_ai | TEXT
- total_count | INTEGER
- merged_count | INTEGER
- updated_at | TEXT

## ai_intelligence
- metric | TEXT
- value | REAL

## ai_thought_log
- id | INTEGER
- task_id | INTEGER
- thought | TEXT
- created_at | TEXT

## ceo_decision_layer_results
- proposal_id | INTEGER
- rank_score | REAL
- meeting_needed | INTEGER
- decision_bucket | TEXT
- summary | TEXT
- source_snapshot | TEXT
- updated_at | TEXT

## ceo_hub_events
- id | INTEGER
- event_type | TEXT
- title | TEXT
- body | TEXT
- proposal_id | INTEGER
- pr_url | TEXT
- created_at | TEXT
- sent_at | TEXT

## company_orders
- id | INTEGER
- source | TEXT
- command | TEXT
- status | TEXT
- created_at | TEXT
- updated_at | TEXT

## contacts
- url | TEXT
- emails | TEXT
- pages | TEXT
- notes | TEXT
- ts | INTEGER

## decision_patterns
- token | TEXT
- weight | REAL
- updated_at | TEXT

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
- created_at | DATETIME

## dev_proposals
- id | INTEGER
- title | TEXT
- description | TEXT
- branch_name | TEXT
- status | TEXT
- risk_level | TEXT
- created_at | DATETIME
- processing | INTEGER
- project_decision | TEXT
- dev_stage | TEXT
- pr_status | TEXT
- pr_url | TEXT
- pr_number | INTEGER
- spec_stage | TEXT
- spec | TEXT
- category | TEXT
- target_system | TEXT
- improvement_type | TEXT
- quality_score | REAL
- priority | INTEGER
- score | REAL
- result_type | TEXT
- guard_status | TEXT
- guard_reason | TEXT
- decision_note | TEXT
- dev_attempts | INTEGER
- last_error | TEXT
- executed_at | TEXT
- source_ai | TEXT
- confidence | REAL
- result_score | REAL
- result_note | TEXT
- notified_at | TEXT
- notified_msg_id | TEXT
- impact_score | REAL
- impact_level | TEXT
- impact_reason | TEXT
- impact_updated_at | TEXT
- target_policy | TEXT

## inbox_commands
- id | INTEGER
- source | TEXT
- text | TEXT
- status | TEXT
- result | TEXT
- created_at | TEXT
- updated_at | TEXT
- chat_id | TEXT
- message_id | INTEGER
- reply_to_message_id | INTEGER
- from_username | TEXT
- from_name | TEXT
- received_at | TEXT
- applied_at | TEXT
- error | TEXT
- update_id | INTEGER
- processed | INTEGER
- router_status | TEXT
- router_target | TEXT
- router_mode | TEXT
- router_finish_status | TEXT

## kaikun02_actions
- id | INTEGER
- proposal_id | INTEGER
- action | TEXT
- created_at | TEXT
- mode | TEXT

## kv
- k | TEXT
- v | TEXT
- updated_at | TEXT

## learning_patterns
- id | INTEGER
- pattern_type | TEXT
- pattern_key | TEXT
- sample_count | INTEGER
- success_count | INTEGER
- avg_impact_score | REAL
- avg_result_score | REAL
- weight | REAL
- updated_at | TEXT

## learning_results
- id | INTEGER
- proposal_id | INTEGER
- title | TEXT
- source_ai | TEXT
- target_system | TEXT
- improvement_type | TEXT
- impact_score | REAL
- impact_level | TEXT
- impact_reason | TEXT
- result_score | REAL
- result_type | TEXT
- result_note | TEXT
- success_flag | INTEGER
- learning_summary | TEXT
- merged_at | TEXT
- created_at | TEXT

## market_chat_jobs
- id | INTEGER
- chat_id | TEXT
- item_id | INTEGER
- role | TEXT
- query | TEXT
- status | TEXT
- error | TEXT
- created_at | TEXT
- updated_at | TEXT

## market_contacts
- id | INTEGER
- item_id | INTEGER
- email | TEXT
- source | TEXT
- created_at | TEXT

## market_items
- id | INTEGER
- url | TEXT
- title | TEXT
- source | TEXT
- status | TEXT
- first_seen_at | TEXT
- last_seen_at | TEXT
- created_at | TEXT

## market_role_briefs
- id | INTEGER
- role | TEXT
- topic | TEXT
- source_url | TEXT
- title | TEXT
- summary | TEXT
- fetched_at | TEXT

## market_state
- k | TEXT
- v | TEXT

## proposal_cluster_stats
- cluster | TEXT
- count | INTEGER

## proposal_clusters
- id | INTEGER
- cluster_key | TEXT
- proposal_id | INTEGER
- title | TEXT
- status | TEXT
- source_ai | TEXT
- created_at | TEXT

## proposal_conversation
- id | INTEGER
- proposal_id | INTEGER
- role | TEXT
- message | TEXT
- created_at | DATETIME

## proposal_state
- proposal_id | INTEGER
- stage | TEXT
- pending_questions | TEXT
- updated_at | DATETIME
- pending_question | TEXT

## reflection_requests
- id | INTEGER
- window_n | INTEGER
- status | TEXT
- result | TEXT
- error | TEXT
- processed_at | TEXT

## retrospectives
- id | INTEGER
- chat_id | TEXT
- from_username | TEXT
- text | TEXT
- created_at | TEXT

## router_tasks
- id | INTEGER
- source_command_id | INTEGER
- mode | TEXT
- target_bot | TEXT
- task_text | TEXT
- status | TEXT
- created_at | TEXT
- updated_at | TEXT
- started_at | TEXT
- finished_at | TEXT
- result_text | TEXT
- timeout_sec | INTEGER
- reply_text | TEXT
- sent_message_id | TEXT

## scout_seen_contacts
- url | TEXT
- emails | TEXT
- pages | TEXT
- notes | TEXT
- ts | INTEGER

## seen
- key | TEXT
- url | TEXT
- title | TEXT
- source | TEXT
- ts | INTEGER

## sqlite_sequence
- name | 
- seq | 

## success_patterns
- pattern | TEXT
- score | REAL
- updated_at | TEXT

## supply_bias
- id | INTEGER
- bias_type | TEXT
- bias_key | TEXT
- weight | REAL
- source_pattern_count | INTEGER
- updated_at | TEXT

## system_metrics
- key | TEXT
- value | TEXT
- updated_at | TEXT

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
- router_ingested | TEXT
- router_ingested_at | TEXT

## tg_prompt_map
- id | INTEGER
- chat_id | TEXT
- message_id | INTEGER
- proposal_id | INTEGER
- kind | TEXT
- created_at | TEXT
