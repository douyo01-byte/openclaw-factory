# OpenClaw LaunchAgent Inventory

## judgment rule
- keep_mainline: 現在の本線で維持対象
- observe_optional: 止まっていても一次障害扱いしない
- legacy_archive_candidate: まず棚卸し対象。即削除はしない

## note
- launchctl の pid/status は「存在」と「直近終了状態」が混在する
- pid があるだけでは常時稼働中と断定しない
- watcher required / observe の判断を優先する

## keep_mainline
- jp.openclaw.ceo_priority_scorer_v1 | pid=49956 | status=1 | interpreted=running_like
- jp.openclaw.dev_pr_watcher_v1 | pid=49045 | status=1 | interpreted=running_like
- jp.openclaw.ops_brain_agent_v1 | pid=42661 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.pattern_extractor_v1 | pid=49759 | status=1 | interpreted=running_like
- jp.openclaw.proposal_cluster_v1 | pid=49665 | status=1 | interpreted=running_like
- jp.openclaw.supply_bias_updater_v1 | pid=49712 | status=1 | interpreted=running_like

## observe_optional
- jp.openclaw.db_integrity_watchdog_v1 | pid=- | status=0 | interpreted=stopped_clean
- jp.openclaw.dev_pr_automerge_v1 | pid=- | status=78 | interpreted=config_or_env_error
- jp.openclaw.kaikun02_coo_controller_v1 | pid=- | status=78 | interpreted=config_or_env_error

## legacy_archive_candidate
- jp.openclaw.ai_employee_manager_v1 | pid=- | status=78 | interpreted=config_or_env_error
- jp.openclaw.ai_employee_ranking_v1 | pid=- | status=78 | interpreted=config_or_env_error
- jp.openclaw.auto_merge_cleaner_v1 | pid=- | status=78 | interpreted=config_or_env_error
- jp.openclaw.ceo_decision_layer_v1 | pid=- | status=127 | interpreted=command_not_found_or_path_error
- jp.openclaw.ceo_execution_selector_v1 | pid=60535 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_executor_candidate_selector_v1 | pid=60541 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_executor_guarded_promoter_v1 | pid=14672 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_executor_lane_digest_v1 | pid=60546 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_executor_normalizer_v1 | pid=98857 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_final_executor_bridge_v1 | pid=27294 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_final_executor_guarded_promoter_v1 | pid=35443 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_final_executor_normalizer_v1 | pid=32020 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_final_executor_row_selector_v1 | pid=60549 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_final_executor_selector_v1 | pid=60555 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_final_guard_bridge_v1 | pid=50064 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_final_guard_normalizer_v1 | pid=52000 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_final_guard_row_selector_v1 | pid=60562 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_final_guard_selector_v1 | pid=60569 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_growth_digest_v1 | pid=60577 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_growth_reviewer_v1 | pid=81516 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_guarded_executor_normalizer_v1 | pid=16231 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_guarded_executor_priority_fixer_v1 | pid=18967 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_guarded_executor_selector_v1 | pid=60584 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_guarded_mainline_priority_fixer_v1 | pid=22377 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_guarded_mainline_promoter_v1 | pid=20867 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_hub_sender_v1 | pid=68368 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_mainline_lane_digest_v1 | pid=60591 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_priority_fixer_v1 | pid=4942 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_problem_digest_v1 | pid=60598 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_promoted_digest_v1 | pid=60603 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_proposal_reviewer_v1 | pid=67432 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_terminal_executor_bridge_v1 | pid=56543 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_terminal_executor_guarded_normalizer_v1 | pid=70452 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_terminal_executor_guarded_promoter_v1 | pid=65949 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_terminal_executor_guarded_selector_v1 | pid=60609 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_terminal_executor_normalizer_v1 | pid=58034 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_terminal_executor_priority_fixer_v1 | pid=63234 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_terminal_executor_selector_v1 | pid=60613 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ceo_terminal_final_executor_bridge_v1 | pid=- | status=127 | interpreted=command_not_found_or_path_error
- jp.openclaw.ceo_terminal_final_executor_normalizer_v1 | pid=- | status=127 | interpreted=command_not_found_or_path_error
- jp.openclaw.ceo_terminal_final_executor_selector_v1 | pid=- | status=127 | interpreted=command_not_found_or_path_error
- jp.openclaw.ceo_terminal_guard_bridge_v1 | pid=- | status=78 | interpreted=config_or_env_error
- jp.openclaw.ceo_terminal_guard_normalizer_v1 | pid=- | status=127 | interpreted=command_not_found_or_path_error
- jp.openclaw.ceo_terminal_guard_selector_v1 | pid=- | status=127 | interpreted=command_not_found_or_path_error
- jp.openclaw.chat_research_job_producer_v1 | pid=- | status=127 | interpreted=command_not_found_or_path_error
- jp.openclaw.chat_research_v1 | pid=- | status=78 | interpreted=config_or_env_error
- jp.openclaw.command_apply_daemon_v1 | pid=90247 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.cto_review_v1 | pid=92594 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.db_integrity_check_v1 | pid=- | status=78 | interpreted=config_or_env_error
- jp.openclaw.db_lock_watchdog_v1 | pid=13580 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.dev_command_executor_v1 | pid=23705 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.dev_merge_notify_v1 | pid=72552 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.evolution_trace_reporter_v1 | pid=94228 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.executor_audit_v1 | pid=- | status=127 | interpreted=command_not_found_or_path_error
- jp.openclaw.executor_guard_v2 | pid=94770 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.healthcheck_v1 | pid=- | status=78 | interpreted=config_or_env_error
- jp.openclaw.impact_judge_v1 | pid=70171 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ingest_private_replies_kaikun02 | pid=80287 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ingest_private_replies_kaikun04 | pid=13260 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.innovation_llm_engine_v1 | pid=30144 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.kaikun02_executor_bridge_v2 | pid=- | status=78 | interpreted=config_or_env_error
- jp.openclaw.kaikun02_health_gate_v1 | pid=- | status=127 | interpreted=command_not_found_or_path_error
- jp.openclaw.kaikun02_router_cleanup_v1 | pid=- | status=78 | interpreted=config_or_env_error
- jp.openclaw.kaikun02_router_worker_v1 | pid=22905 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.kaikun04_router_cleanup_v1 | pid=- | status=78 | interpreted=config_or_env_error
- jp.openclaw.kaikun04_router_worker_v1 | pid=22909 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.learning_result_writer_v1 | pid=44927 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.open_pr_guard_v1 | pid=44936 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.ops_brain_watcher_v1 | pid=20440 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.pr_stall_watchdog_v1 | pid=13812 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.private_reply_to_inbox_v1 | pid=80155 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.proposal_dedupe_v1 | pid=44835 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.proposal_throttle_engine_v1 | pid=45144 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.router_reply_finisher_v1 | pid=50270 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.router_stall_watchdog_v1 | pid=13698 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.scout_market_v2 | pid=- | status=127 | interpreted=command_not_found_or_path_error
- jp.openclaw.secretary_llm_v1 | pid=- | status=127 | interpreted=command_not_found_or_path_error
- jp.openclaw.self_evolution_engine_v1 | pid=47084 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.self_improvement_engine_v2 | pid=86832 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.target_policy_guard_v1 | pid=45235 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.task_router_v1 | pid=50267 | status=-15 | interpreted=terminated_or_recently_stopped
- jp.openclaw.tg_private_ingest_v1 | pid=- | status=78 | interpreted=config_or_env_error
