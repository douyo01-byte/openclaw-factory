# OpenClaw Handover

## Database
- canonical DB: `/Users/doyopc/AI/openclaw-factory/data/openclaw.db`

## Current confirmed pipelines
### Dev pipeline
proposal_promoter_v1
-> spec_refiner_v2
-> spec_decomposer_v1
-> dev_pr_creator_v1
-> dev_pr_watcher_v1
-> dev_pr_automerge_v1
-> auto_merge_cleaner_v1

### Learning / scoring
proposal_ranking_v1
-> ceo_priority_scorer_v1
-> ceo_hub_sender_v1
-> impact_judge_v1
-> pattern_extractor_v1
-> proposal_cluster_v1
-> supply_bias_updater_v1
-> self_improvement_engine_v2
-> ai_employee_manager_v1
-> ai_employee_ranking_v1

### Router / reply
task_router_v1
-> kaikun02_router_worker_v1 / kaikun04_router_worker_v1
-> ingest_private_replies_kaikun02 / ingest_private_replies_kaikun04
-> private_reply_to_inbox_v1
-> router_reply_finisher_v1

### Control
kaikun02_health_gate_v1
-> ai_employee_manager_v1
-> ai_employee_ranking_v1
-> kaikun02_coo_controller_v1
-> kaikun02_executor_bridge_v2

## Known non-primary legacy line
- archive/legacy_runtime/bots/chat_router_v1.py
- archive/legacy_runtime/bots/dev_router_v1.py
- archive/legacy_runtime/bots/tg_inbox_poll_v1.py
- archive/legacy_runtime/bots/tg_inbox_poll_daemon_v1.py

## Handover rule
- prefer runtime reality over older historical docs
- prefer active router line over old inbox/router line
- prefer absolute canonical DB over relative `data/openclaw.db`

## Runtime classification
- canonical file: `reports/audit_20260316/runtime_classification_20260316.md`
- ACTIVE = current production/runtime path
- RESERVE_IMPLEMENTED = code exists but is not connected to current production path
- reserve files with unknown/legacy table refs must not be treated as active runtime

## Reserve reclassification update
- canonical fix file: `reports/audit_20260317/reserve_reclassification.md`
- `chat_research_v1.py`, `db_integrity_check_v1.py`, `healthcheck_v1.py`, `open_pr_guard_v1.py` are runtime-connected and must not be treated as reserve-only
- current true reserve keep set is limited to 7 files under old command/meeting/team paths
