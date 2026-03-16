🗂 OpenClaw Runtime分 類

# Runtime Classification (2026-03-16)

## ACTIVE
- proposal_promoter_v1
- spec_refiner_v2
- spec_decomposer_v1
- dev_pr_creator_v1
- dev_pr_watcher_v1
- auto_merge_cleaner_v1
- secretary_llm_v1
- task_router_v1
- kaikun02_router_worker_v1
- kaikun02_health_gate_v1
- kaikun02_coo_controller_v1
- kaikun02_executor_bridge_v2
- ai_employee_manager_v1
- ai_employee_ranking_v1
- dev_pr_automerge_v1
- learning_brain_v1
- innovation_llm_engine_v1

## RESERVE_IMPLEMENTED
- bots/command_apply_v1.py
- bots/meeting_from_db_v1.py
- bots/team/aya_judge.py
- bots/team/daiki_analyst.py
- bots/team/kenji_researcher.py
- bots/team/miho_finder.py
- bots/team/sakura_scout.py

## JUDGMENT
- ACTIVE is connected to current LaunchAgent/runtime path.
- RESERVE_IMPLEMENTED has code and git history but is not connected to current active runtime.
- These reserve files include legacy/unknown table refs and should not be treated as current production path.

# Reserve Final Decision (2026-03-17)

## KEEP_NOT_ACTIVE
- bots/command_apply_v1.py
- bots/meeting_from_db_v1.py
- bots/team/aya_judge.py
- bots/team/daiki_analyst.py
- bots/team/kenji_researcher.py
- bots/team/miho_finder.py
- bots/team/sakura_scout.py

## DECISION
- These files remain in repository.
- They are implemented assets, not current active runtime.
- They must not be counted as ACTIVE unless LaunchAgent/runtime path is explicitly restored.
- They are not archive targets at this time.

## ACTIVE_RECLASSIFIED
- bots/chat_research_v1.py
- bots/db_integrity_check_v1.py
- bots/healthcheck_v1.py
- bots/open_pr_guard_v1.py
