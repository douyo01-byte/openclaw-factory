# Runtime Unified Inventory (2026-03-17)

## Policy refs
- reports/audit_20260317/active_runtime_flow_table.md
- reports/audit_20260317/kaikun02_route_policy.md
- reports/audit_20260317/kaikun04_role_policy.md
- reports/audit_20260317/keep_not_active_reactivation_guide.md
- reports/audit_20260317/reserve_final_decision.md
- reports/audit_20260317/task_router_policy.md

| path | class | launchagent | quick | relay_only | cleanup | sanity | tracked | last_commit |
|---|---|---|---|---|---|---|---|---|
| bots/proposal_promoter_v1.py | IMPLEMENTED_UNCONNECTED | - | no | no | no | no | yes | 52a9bdc Stabilize promoter refiner decomposer pipeline after zero backlog |
| bots/spec_refiner_v2.py | IMPLEMENTED_UNCONNECTED | - | no | no | no | no | yes | 52a9bdc Stabilize promoter refiner decomposer pipeline after zero backlog |
| bots/spec_decomposer_v1.py | IMPLEMENTED_UNCONNECTED | - | no | no | no | no | yes | 52a9bdc Stabilize promoter refiner decomposer pipeline after zero backlog |
| bots/dev_pr_creator_v1.py | IMPLEMENTED_UNCONNECTED | - | no | no | no | no | yes | 5212a18 Stabilize PR creator/watcher and add audit reports |
| bots/dev_pr_watcher_v1.py | IMPLEMENTED_UNCONNECTED | - | no | no | no | no | yes | 0856303 Restore merged rows block in watcher |
| bots/auto_merge_cleaner_v1.py | IMPLEMENTED_UNCONNECTED | - | no | no | no | no | yes | 4f421fc Add auto merge cleaner for open PR backlog |
| bots/secretary_llm_v1.py | IMPLEMENTED_UNCONNECTED | - | no | no | no | yes | yes | cdbdced Use merged runtime classification source in replies |
| bots/task_router_v1.py | IMPLEMENTED_UNCONNECTED | - | no | no | no | yes | yes | 6501a58 Add router layer with FAST/THINK workers and timeout finisher |
| bots/kaikun02_router_worker_v1.py | IMPLEMENTED_UNCONNECTED | - | yes | no | no | yes | yes | 9d41aa7 Normalize kaikun02 quick route matching |
| bots/kaikun02_router_cleanup_v1.py | IMPLEMENTED_UNCONNECTED | - | no | no | yes | yes | yes | b956c79 Add kaikun02 router cleanup for stale quick-route tasks |
| bots/kaikun02_health_gate_v1.py | IMPLEMENTED_UNCONNECTED | - | no | no | no | no | yes | 577c10a Add Kaikun02 health gate and auto-stop enforcement |
| bots/kaikun02_coo_controller_v1.py | IMPLEMENTED_UNCONNECTED | - | no | no | no | no | yes | 053bdaa Restore private reply ingest flow for Kaikun02/04 |
| bots/kaikun02_executor_bridge_v2.py | IMPLEMENTED_UNCONNECTED | - | no | no | no | no | yes | c446a4f Stabilize post-backlog zero state and reduce idle executor noise |
| bots/kaikun04_router_worker_v1.py | ACTIVE_RELAY_ONLY | - | no | yes | no | no | yes | d477583 Stabilize router worker and reply finisher |
| bots/kaikun04_router_cleanup_v1.py | IMPLEMENTED_UNCONNECTED | - | no | no | yes | yes | yes | bea23a5 Add kaikun04 cleanup and sanity checks |
| bots/ai_employee_manager_v1.py | IMPLEMENTED_UNCONNECTED | - | no | no | no | no | yes | ca380bf Use timezone aware UTC in ai employee manager |
| bots/ai_employee_ranking_v1.py | IMPLEMENTED_UNCONNECTED | - | no | no | no | no | yes | 056cc73 Add tracked ai employee ranking bot and runner |
| bots/dev_pr_automerge_v1.py | IMPLEMENTED_UNCONNECTED | - | no | no | no | no | yes | ae2066a Restore CEO reply loop and executor auto-flow |
| bots/learning_brain_v1.py | IMPLEMENTED_UNCONNECTED | - | no | no | no | no | yes | 21c506f pr5: guard learning_result ordering after merged event |
| bots/innovation_llm_engine_v1.py | IMPLEMENTED_UNCONNECTED | - | no | no | no | no | yes | e42febe Tune innovation target rotation and supply rate |
| bots/chat_research_v1.py | IMPLEMENTED_UNCONNECTED | - | no | no | no | no | yes | 2d85838 Reconnect code review and migrate business bots to market tables |
| bots/db_integrity_check_v1.py | IMPLEMENTED_UNCONNECTED | - | no | no | no | no | yes | 1644802 Exclude normal throttled states from db integrity metric |
| bots/healthcheck_v1.py | IMPLEMENTED_UNCONNECTED | - | no | no | no | no | yes | fa17fb2 Fix learning results schema and wire priority scoring |
| bots/open_pr_guard_v1.py | IMPLEMENTED_UNCONNECTED | - | no | no | no | no | yes | 1c926d1 Stabilize unique open PR guard and branch isolation |
| bots/command_apply_v1.py | KEEP_NOT_ACTIVE | - | no | no | no | no | yes | c0a39a3 ci: auto fix (20260302-224953) |
| bots/meeting_from_db_v1.py | KEEP_NOT_ACTIVE | - | no | no | no | no | yes | c0a39a3 ci: auto fix (20260302-224953) |
| bots/team/aya_judge.py | KEEP_NOT_ACTIVE | - | no | no | no | no | yes | c0a39a3 ci: auto fix (20260302-224953) |
| bots/team/daiki_analyst.py | KEEP_NOT_ACTIVE | - | no | no | no | no | yes | c0a39a3 ci: auto fix (20260302-224953) |
| bots/team/kenji_researcher.py | KEEP_NOT_ACTIVE | - | no | no | no | no | yes | c0a39a3 ci: auto fix (20260302-224953) |
| bots/team/miho_finder.py | KEEP_NOT_ACTIVE | - | no | no | no | no | yes | c0a39a3 ci: auto fix (20260302-224953) |
| bots/team/sakura_scout.py | KEEP_NOT_ACTIVE | - | no | no | no | no | yes | c0a39a3 ci: auto fix (20260302-224953) |

## Summary
- ACTIVE: 0
- ACTIVE_RELAY_ONLY: 1
- KEEP_NOT_ACTIVE: 7
- IMPLEMENTED_UNCONNECTED: 23
- UNCONFIRMED: 0

