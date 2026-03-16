# OpenClaw Current State

## Source of truth
- runtime DB: `/Users/doyopc/AI/openclaw-factory/data/openclaw.db`
- primary repo for runtime truth: `openclaw-factory-daemon`
- current stage: post-static-burn-in-pre-runtime-burn-in

## Current active core
- proposal_promoter_v1
- spec_refiner_v2
- spec_decomposer_v1
- dev_pr_creator_v1
- dev_pr_watcher_v1
- dev_pr_automerge_v1
- auto_merge_cleaner_v1

## Current active intelligence / learning
- proposal_ranking_v1
- ceo_priority_scorer_v1
- ceo_hub_sender_v1
- impact_judge_v1
- pattern_extractor_v1
- proposal_cluster_v1
- supply_bias_updater_v1
- self_improvement_engine_v2
- cto_review_v1
- ai_employee_manager_v1
- ai_employee_ranking_v1

## Current active control / safety
- command_apply_daemon_v1
- executor_guard_v2
- healthcheck_v1
- db_integrity_watchdog_v1
- kaikun02_health_gate_v1
- kaikun02_coo_controller_v1
- kaikun02_executor_bridge_v2

## Current active router / reply
- task_router_v1
- kaikun02_router_worker_v1
- kaikun04_router_worker_v1
- private_reply_to_inbox_v1
- router_reply_finisher_v1
- router_timeout_watchdog_v1
- ingest_private_replies_kaikun02
- ingest_private_replies_kaikun04

## Current integrity state
- open_pr_count = 0
- blank_source_ai = 0
- merged_without_result_type = 0
- stage_divergence_count = 0
- lifecycle_anomaly_count = 0
- missing_source_category_target_system = 0

## Current reality note
- old router / inbox line was moved to archive/legacy_runtime and is not current primary path
- docs older than 2026-03-16 may contain pre-router-refresh state
- Kaikun02 should treat this file as highest-priority runtime summary
- secretary_llm_v1 dashboard now includes ai employee ranking from ai_employee_rankings

## Runtime classification
- canonical file: `reports/audit_20260316/runtime_classification_20260316.md`
- ACTIVE = current production/runtime path
- RESERVE_IMPLEMENTED = code exists but is not connected to current production path
- reserve files with unknown/legacy table refs must not be treated as active runtime

## Reserve reclassification update
- canonical fix file: `reports/audit_20260317/reserve_reclassification.md`
- `chat_research_v1.py`, `db_integrity_check_v1.py`, `healthcheck_v1.py`, `open_pr_guard_v1.py` are runtime-connected and must not be treated as reserve-only
- current true reserve keep set is limited to 7 files under old command/meeting/team paths

## Reserve final decision
- canonical file: `reports/audit_20260317/reserve_final_decision.md`
- current reserve set is KEEP_NOT_ACTIVE, not archive
- these files are implemented assets kept in repo but excluded from active runtime count
