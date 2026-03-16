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

### Router / reply
task_router_v1
-> kaikun02_router_worker_v1 / kaikun04_router_worker_v1
-> ingest_private_replies_kaikun02 / ingest_private_replies_kaikun04
-> private_reply_to_inbox_v1
-> router_reply_finisher_v1

### Control
kaikun02_health_gate_v1
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
