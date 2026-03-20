# META KEEP HOLD

## KEEP
- jp.openclaw.command_apply_daemon_v1
- jp.openclaw.db_lock_watchdog_v1
- jp.openclaw.db_integrity_watchdog_v1
- jp.openclaw.dev_command_executor_v1
- jp.openclaw.dev_merge_notify_v1
- jp.openclaw.executor_guard_v2
- jp.openclaw.open_pr_guard_v1
- jp.openclaw.ops_brain_watcher_v1
- jp.openclaw.pr_stall_watchdog_v1
- jp.openclaw.proposal_dedupe_v1
- jp.openclaw.proposal_throttle_engine_v1
- jp.openclaw.target_policy_guard_v1

## FULL_RETIRE
- jp.openclaw.cto_review_v1
- jp.openclaw.self_evolution_engine_v1
- jp.openclaw.self_improvement_engine_v2
- jp.openclaw.learning_result_writer_v1
- jp.openclaw.innovation_llm_engine_v1
- jp.openclaw.impact_judge_v1
- jp.openclaw.evolution_trace_reporter_v1

## RULE
- KEEP は 現在構造に必要
- FULL_RETIRE は 復活禁止
- 再度必要な場合も 新規bot復活ではなく mainline統合前提で再判断
- db_integrity_watchdog_v1 は observe 対象として保持
