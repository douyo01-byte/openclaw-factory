# OpenClaw Inventory Decision

## LaunchAgents
- keep:
  tg_poll_loop
  private_reply_to_inbox_v1
  router_reply_finisher_v1
  telegram_ops_executor_v1
  kaikun04_router_worker_v1
  self_improvement_to_learning_v1
  self_improvement_pattern_bridge_v1
  self_improvement_feedback_metrics_v1
  ingest_private_replies_kaikun04
  ops_brain_agent_v1
  secretary_llm_v1

- integrate:
  task_router_v1
  kaikun04_exec_bridge_v1

- stop_candidate:
  router_timeout_watchdog_v1
  router_stall_watchdog_v1
  router_timeout_fallback_v1
  kaikun04_router_cleanup_v1
  business_sample_watcher_v1

## DB Core
- inbox_commands
- router_tasks
- conversation_jobs
- conversation_artifacts
- learning_results
- learning_patterns
- self_improvement_log

## Notes
- OpenClawのコアはすでに成立している
- 現在は削減と統合フェーズ
