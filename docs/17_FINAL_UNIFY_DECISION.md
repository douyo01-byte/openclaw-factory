# FINAL UNIFY DECISION

## Keep as current primary path
- proposal_promoter_v1
- spec_refiner_v2
- spec_decomposer_v1
- dev_pr_creator_v1
- dev_pr_watcher_v1
- dev_pr_automerge_v1
- auto_merge_cleaner_v1
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
- command_apply_daemon_v1
- executor_guard_v2
- healthcheck_v1
- db_integrity_watchdog_v1
- kaikun02_health_gate_v1
- kaikun02_coo_controller_v1
- kaikun02_executor_bridge_v2
- task_router_v1
- kaikun02_router_worker_v1
- kaikun04_router_worker_v1
- private_reply_to_inbox_v1
- router_reply_finisher_v1
- router_timeout_watchdog_v1
- dev_merge_notify_v1
- ai_employee_manager_v1
- ai_employee_ranking_v1

## Keep but non-primary / reserve / historical
- archive/legacy_runtime/bots/chat_router_v1.py
- archive/legacy_runtime/bots/dev_router_v1.py
- archive/legacy_runtime/bots/tg_inbox_poll_v1.py
- archive/legacy_runtime/bots/tg_inbox_poll_daemon_v1.py
- chat_research_v1
- scout_market_v1
- scout_market_v2
- ai_ceo_engine_v1
- ai_employee_factory_v1
- strategy_engine_v1
- innovation_engine_v1

## DB unification policy
- preferred env order:
  1. OCLAW_DB_PATH
  2. FACTORY_DB_PATH
  3. DB_PATH
  4. `/Users/doyopc/AI/openclaw-factory/data/openclaw.db`
- avoid relative `data/openclaw.db` in current primary runtime code

## Kaikun02 policy
- Kaikun02 should prioritize:
  1. docs/06_CURRENT_STATE.md
  2. docs/08_HANDOVER.md
  3. docs/14_ACTIVE_AGENTS_FINAL.md
- older audit docs are historical support only

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

## KEEP_NOT_ACTIVE reactivation guide
- canonical file: `reports/audit_20260317/keep_not_active_reactivation_guide.md`
- reserve keep set should only be re-enabled with explicit DB / LaunchAgent / I/O checks
- do not restore these 7 files directly into ACTIVE without a per-file reactivation pass

## Active runtime flow table
- canonical file: `reports/audit_20260317/active_runtime_flow_table.md`
- use this as the single operational map of ACTIVE bots
- Kaikun02 / mother chat should explain runtime using this table first

## Kaikun02 quick routes
- canonical file: `reports/audit_20260317/kaikun02_quick_routes.md`
- quick reply active: dashboard / next_tasks / weak_points / ai_employee_ranking / runtime_classification / flow_bottleneck / top_watchpoints
- anything else should be treated as normal relay task

## Kaikun02 route policy
- canonical file: `reports/audit_20260317/kaikun02_route_policy.md`
- quick reply と relay の境界はこのファイルを正とする
- quick route 追加時は cleanup条件と final sanity grep を同時更新する

## Kaikun04 role policy
- canonical file: `reports/audit_20260317/kaikun04_role_policy.md`
- Kaikun04 = THINK / deep analysis / relay-only
- Kaikun04 must not receive quick routes under current policy
- quick reply responsibility stays on Kaikun02

## Task router policy
- canonical file: `reports/audit_20260317/task_router_policy.md`
- task_router_v1 must classify quick operational questions to Kaikun02
- task_router_v1 must classify THINK / heavy analysis to Kaikun04
- router policy changes must be reflected in both docs and runtime cleanup rules
