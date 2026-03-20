# OPENCLAW CONNECTED RUNTIME PATCH

## 現在の最小実働
- open_pr_guard_v1
- dev_pr_watcher_v1
- dev_pr_creator_v1

## 接続済み確認
- docs正本を dev/self-watch-recovery から復元
- audit_20260315 のログを基に bot / plist / runtime / DB の接続台帳を生成

## 接続台帳

# CONNECTED ASSET INVENTORY

## SUMMARY
- bot_files_count: 91
- active_labels_detected: 3
- plist_labels_detected: 95

## SOURCE_AI SUMMARY
- mothership: total=901 open_rows=6
- (blank): total=716 open_rows=0
- executor_sweep: total=661 open_rows=0
- innovation_llm_engine_v1: total=205 open_rows=0
- self_improve: total=53 open_rows=0
- cto: total=38 open_rows=3
- innovation_engine: total=26 open_rows=4
- strategy_engine: total=8 open_rows=2
- ai_meeting_engine_v1: total=6 open_rows=0
- coo: total=4 open_rows=0
- mothership_orphan_closed: total=1 open_rows=0

## BOT CONNECTION TABLE
| bot | label | class | domain | plist |
|---|---|---|---|---|
| __init__ | jp.openclaw.__init__ | no_plist | other |  |
| ai_ceo_engine_v1 | jp.openclaw.ai_ceo_engine_v1 | no_plist | org_runtime |  |
| ai_employee_factory_v1 | jp.openclaw.ai_employee_factory_v1 | no_plist | other |  |
| ai_employee_manager_v1 | jp.openclaw.ai_employee_manager_v1 | plist_only | other | jp.openclaw.ai_employee_manager_v1.plist |
| ai_meeting_digest_v1 | jp.openclaw.ai_meeting_digest_v1 | plist_only | org_runtime | jp.openclaw.ai_meeting_digest_v1.plist |
| ai_meeting_engine_v1 | jp.openclaw.ai_meeting_engine_v1 | no_plist | org_runtime |  |
| auto_execute_now_v1 | jp.openclaw.auto_execute_now_v1 | plist_only | other | jp.openclaw.auto_execute_now_v1.plist |
| brain_supply_v1 | jp.openclaw.brain_supply_v1 | plist_only | producer_learning | jp.openclaw.brain_supply_v1.plist |
| build_decision_patterns | jp.openclaw.build_decision_patterns | no_plist | other |  |
| ceo_decision_layer_v1 | jp.openclaw.ceo_decision_layer_v1 | plist_only | org_runtime | jp.openclaw.ceo_decision_layer_v1.plist |
| ceo_hub_sender_v1 | jp.openclaw.ceo_hub_sender_v1 | plist_only | org_runtime | jp.openclaw.ceo_hub_sender_v1.plist |
| ceo_priority_scorer_v1 | jp.openclaw.ceo_priority_scorer_v1 | plist_only | org_runtime | jp.openclaw.ceo_priority_scorer_v1.plist |
| chat_research_v1 | jp.openclaw.chat_research_v1 | plist_only | other | jp.openclaw.chat_research_v1.plist |
| chat_router_v1 | jp.openclaw.chat_router_v1 | no_plist | dev_pipeline |  |
| code_review_engine_v1 | jp.openclaw.code_review_engine_v1 | no_plist | other |  |
| command_apply_daemon_v1 | jp.openclaw.command_apply_daemon_v1 | plist_only | other | jp.openclaw.command_apply_daemon_v1.plist |
| command_apply_v1 | jp.openclaw.command_apply_v1 | no_plist | other |  |
| company_health_score_v1 | jp.openclaw.company_health_score_v1 | plist_only | ops_db | jp.openclaw.company_health_score_v1.plist |
| cto_review_v1 | jp.openclaw.cto_review_v1 | plist_only | other | jp.openclaw.cto_review_v1.plist |
| db_integrity_check_v1 | jp.openclaw.db_integrity_check_v1 | plist_only | ops_db | jp.openclaw.db_integrity_check_v1.plist |
| db_integrity_watchdog_v1 | jp.openclaw.db_integrity_watchdog_v1 | plist_only | ops_db | jp.openclaw.db_integrity_watchdog_v1.plist |
| dev_auto_execute_v1 | jp.openclaw.dev_auto_execute_v1 | no_plist | other |  |
| dev_command_executor_v1 | jp.openclaw.dev_command_executor_v1 | plist_only | dev_pipeline | jp.openclaw.dev_command_executor_v1.plist |
| dev_executor_v1 | jp.openclaw.dev_executor_v1 | no_plist | dev_pipeline |  |
| dev_meeting_telegram_bridge_v1 | jp.openclaw.dev_meeting_telegram_bridge_v1 | plist_only | org_runtime | jp.openclaw.dev_meeting_telegram_bridge_v1.plist |
| dev_merge_notify_v1 | jp.openclaw.dev_merge_notify_v1 | plist_only | other | jp.openclaw.dev_merge_notify_v1.plist |
| dev_pr_automerge_v1 | jp.openclaw.dev_pr_automerge_v1 | plist_only | other | jp.openclaw.dev_pr_automerge_v1.plist |
| dev_pr_creator_v1 | jp.openclaw.dev_pr_creator_v1 | active | dev_pipeline | jp.openclaw.dev_pr_creator_v1.plist |
| dev_pr_watcher_v1 | jp.openclaw.dev_pr_watcher_v1 | active | dev_pipeline | jp.openclaw.dev_pr_watcher_v1.plist |
| dev_proposal_notify_daemon_v1 | jp.openclaw.dev_proposal_notify_daemon_v1 | no_plist | producer_learning |  |
| dev_proposal_notify_v1 | jp.openclaw.dev_proposal_notify_v1 | plist_only | producer_learning | jp.openclaw.dev_proposal_notify_v1.plist |
| dev_reviewer_v1 | jp.openclaw.dev_reviewer_v1 | no_plist | other |  |
| dev_router_v1 | jp.openclaw.dev_router_v1 | plist_only | dev_pipeline | jp.openclaw.dev_router_v1.plist |
| enrich_contacts_v1 | jp.openclaw.enrich_contacts_v1 | no_plist | other |  |
| executor_audit_v1 | jp.openclaw.executor_audit_v1 | plist_only | dev_pipeline | jp.openclaw.executor_audit_v1.plist |
| executor_guard_v1 | jp.openclaw.executor_guard_v1 | no_plist | dev_pipeline |  |
| executor_guard_v2 | jp.openclaw.executor_guard_v2 | plist_only | dev_pipeline | jp.openclaw.executor_guard_v2.plist |
| healthcheck_v1 | jp.openclaw.healthcheck_v1 | plist_only | ops_db | jp.openclaw.healthcheck_v1.plist |
| impact_judge_v1 | jp.openclaw.impact_judge_v1 | plist_only | other | jp.openclaw.impact_judge_v1.plist |
| ingest_private_replies_v1 | jp.openclaw.ingest_private_replies_v1 | plist_only | other | jp.openclaw.ingest_private_replies_v1.plist |
| ingest_spec_answers_v1 | jp.openclaw.ingest_spec_answers_v1 | no_plist | other |  |
| ingest_spec_reply_v1 | jp.openclaw.ingest_spec_reply_v1 | no_plist | telegram_io |  |
| ingest_telegram_replies_v1 | jp.openclaw.ingest_telegram_replies_v1 | no_plist | telegram_io |  |
| innovation_engine_v1 | jp.openclaw.innovation_engine_v1 | plist_only | producer_learning | jp.openclaw.innovation_engine_v1.plist |
| innovation_llm_engine_v1 | jp.openclaw.innovation_llm_engine_v1 | plist_only | producer_learning | jp.openclaw.innovation_llm_engine_v1.plist |
| kaikun02_router_worker_v1 | jp.openclaw.kaikun02_router_worker_v1 | plist_only | dev_pipeline | jp.openclaw.kaikun02_router_worker_v1.plist |
| kaikun04_router_worker_v1 | jp.openclaw.kaikun04_router_worker_v1 | plist_only | dev_pipeline | jp.openclaw.kaikun04_router_worker_v1.plist |
| learning_brain_v1 | jp.openclaw.learning_brain_v1 | plist_only | other | jp.openclaw.learning_brain_v1.plist |
| learning_result_writer_v1 | jp.openclaw.learning_result_writer_v1 | plist_only | other | jp.openclaw.learning_result_writer_v1.plist |
| mainstream_fallback_supply_v1 | jp.openclaw.mainstream_fallback_supply_v1 | no_plist | producer_learning |  |
| meeting_from_db_v1 | jp.openclaw.meeting_from_db_v1 | no_plist | org_runtime |  |
| meeting_orchestrator_v1 | jp.openclaw.meeting_orchestrator_v1 | plist_only | org_runtime | jp.openclaw.meeting_orchestrator_v1.plist |
| open_pr_guard_v1 | jp.openclaw.open_pr_guard_v1 | active | dev_pipeline | jp.openclaw.open_pr_guard_v1.plist |
| parse_dev_reply_v1 | jp.openclaw.parse_dev_reply_v1 | plist_only | telegram_io | jp.openclaw.parse_dev_reply_v1.plist |
| pattern_extractor_v1 | jp.openclaw.pattern_extractor_v1 | plist_only | other | jp.openclaw.pattern_extractor_v1.plist |
| private_reply_to_inbox_v1 | jp.openclaw.private_reply_to_inbox_v1 | plist_only | telegram_io | jp.openclaw.private_reply_to_inbox_v1.plist |
| proposal_builder_loop_v1 | jp.openclaw.proposal_builder_loop_v1 | plist_only | producer_learning | jp.openclaw.proposal_builder_loop_v1.plist |
| proposal_cluster_v1 | jp.openclaw.proposal_cluster_v1 | plist_only | producer_learning | jp.openclaw.proposal_cluster_v1.plist |
| proposal_dedupe_v1 | jp.openclaw.proposal_dedupe_v1 | plist_only | producer_learning | jp.openclaw.proposal_dedupe_v1.plist |
| proposal_promoter_v1 | jp.openclaw.proposal_promoter_v1 | plist_only | producer_learning | jp.openclaw.proposal_promoter_v1.plist |
| proposal_ranking_v1 | jp.openclaw.proposal_ranking_v1 | plist_only | producer_learning | jp.openclaw.proposal_ranking_v1.plist |
| proposal_throttle_engine_v1 | jp.openclaw.proposal_throttle_engine_v1 | plist_only | producer_learning | jp.openclaw.proposal_throttle_engine_v1.plist |
| reasoning_engine_v1 | jp.openclaw.reasoning_engine_v1 | plist_only | producer_learning | jp.openclaw.reasoning_engine_v1.plist |
| reflection_v1 | jp.openclaw.reflection_v1 | plist_only | other | jp.openclaw.reflection_v1.plist |
| reflection_worker_v1 | jp.openclaw.reflection_worker_v1 | plist_only | other | jp.openclaw.reflection_worker_v1.plist |
| router_reply_finisher_v1 | jp.openclaw.router_reply_finisher_v1 | plist_only | dev_pipeline | jp.openclaw.router_reply_finisher_v1.plist |
| router_timeout_watchdog_v1 | jp.openclaw.router_timeout_watchdog_v1 | plist_only | dev_pipeline | jp.openclaw.router_timeout_watchdog_v1.plist |
| schema_guardian_v1 | jp.openclaw.schema_guardian_v1 | plist_only | dev_pipeline | jp.openclaw.schema_guardian_v1.plist |
| schema_migration_engine_v1 | jp.openclaw.schema_migration_engine_v1 | plist_only | ops_db | jp.openclaw.schema_migration_engine_v1.plist |
| scout_market_v2 | jp.openclaw.scout_market_v2 | plist_only | other | jp.openclaw.scout_market_v2.plist |
| secretary_llm_v1 | jp.openclaw.secretary_llm_v1 | plist_only | org_runtime | jp.openclaw.secretary_llm_v1.plist |
| self_healing_v2 | jp.openclaw.self_healing_v2 | plist_only | other | jp.openclaw.self_healing_v2.plist |
| self_improvement_engine_v2 | jp.openclaw.self_improvement_engine_v2 | plist_only | other | jp.openclaw.self_improvement_engine_v2.plist |
| self_repair_engine_v1 | jp.openclaw.self_repair_engine_v1 | no_plist | other |  |
| self_strength_watchdog_v1 | jp.openclaw.self_strength_watchdog_v1 | plist_only | ops_db | jp.openclaw.self_strength_watchdog_v1.plist |
| spec_decomposer_v1 | jp.openclaw.spec_decomposer_v1 | plist_only | other | jp.openclaw.spec_decomposer_v1.plist |
| spec_notify_v1 | jp.openclaw.spec_notify_v1 | plist_only | other | jp.openclaw.spec_notify_v1.plist |
| spec_refiner_v2 | jp.openclaw.spec_refiner_v2 | plist_only | other | jp.openclaw.spec_refiner_v2.plist |
| strategy_engine_v1 | jp.openclaw.strategy_engine_v1 | plist_only | producer_learning | jp.openclaw.strategy_engine_v1.plist |
| supply_adoption_metrics_v1 | jp.openclaw.supply_adoption_metrics_v1 | plist_only | producer_learning | jp.openclaw.supply_adoption_metrics_v1.plist |
| supply_bias_updater_v1 | jp.openclaw.supply_bias_updater_v1 | plist_only | producer_learning | jp.openclaw.supply_bias_updater_v1.plist |
| sync_execute_stage_v1 | jp.openclaw.sync_execute_stage_v1 | no_plist | other |  |
| sync_executor_ready_v1 | jp.openclaw.sync_executor_ready_v1 | no_plist | dev_pipeline |  |
| sync_pr_ready_v1 | jp.openclaw.sync_pr_ready_v1 | no_plist | other |  |
| target_policy_guard_v1 | jp.openclaw.target_policy_guard_v1 | plist_only | dev_pipeline | jp.openclaw.target_policy_guard_v1.plist |
| task_router_v1 | jp.openclaw.task_router_v1 | plist_only | dev_pipeline | jp.openclaw.task_router_v1.plist |
| tg_inbox_poll_daemon_v1 | jp.openclaw.tg_inbox_poll_daemon_v1 | no_plist | telegram_io |  |
| tg_inbox_poll_v1 | jp.openclaw.tg_inbox_poll_v1 | no_plist | telegram_io |  |
| tg_poll_loop_v2 | jp.openclaw.tg_poll_loop_v2 | plist_only | telegram_io | jp.openclaw.tg_poll_loop_v2.plist |
| tg_send_reflection_v1 | jp.openclaw.tg_send_reflection_v1 | plist_only | telegram_io | jp.openclaw.tg_send_reflection_v1.plist |
| watchdog_v1 | jp.openclaw.watchdog_v1 | plist_only | ops_db | jp.openclaw.watchdog_v1.plist |

## パイプライン hotspot

```
2633|MotherShip: health CLI|mothership|open|execute_now|open|decomposed|open|0|dev/mothership-health-cli-e61cca|https://github.com/douyo01-byte/openclaw-factory/pull/2353
2630|Strategy innovation executor cd93f4|strategy_engine|open|execute_now|open|raw|open|0|dev/batch-2630-2632|https://github.com/douyo01-byte/openclaw-factory/pull/2347
2629|🧠 Kaikun04 CTOレビュー|cto|open|execute_now|open|decomposed|open|0|dev/batch-2629-2629|https://github.com/douyo01-byte/openclaw-factory/pull/2346
2628|MotherShip: db check|mothership|open|execute_now|open|raw|open|0|dev/batch-2628-2628|https://github.com/douyo01-byte/openclaw-factory/pull/2345
2626|Innovation improvement self_improve 7635f1|innovation_engine|open|execute_now|open|decomposed|open|0|dev/innovation-self-improve-7635f1|https://github.com/douyo01-byte/openclaw-factory/pull/2350
2624|Innovation improvement executor 077e49|innovation_engine|open|execute_now|open|refined|open|0|dev/batch-2624-2627|https://github.com/douyo01-byte/openclaw-factory/pull/2344
2622|Strategy innovation executor 646eb6|strategy_engine|open|execute_now|open|refined|open|0|dev/batch-2622-2623|https://github.com/douyo01-byte/openclaw-factory/pull/2343
2620|Innovation improvement self_improve d50f8b|innovation_engine|open|execute_now|open|decomposed|open|0|dev/batch-2620-2620|https://github.com/douyo01-byte/openclaw-factory/pull/2342
2618|Innovation improvement executor a6da08|innovation_engine|open|execute_now|open|refined|open|0|dev/batch-2618-2621|https://github.com/douyo01-byte/openclaw-factory/pull/2341
2617|🧠 Kaikun04 CTOレビュー|cto|open|execute_now|open||open|0|dev/batch-2617-2616|https://github.com/douyo01-byte/openclaw-factory/pull/2340
2615|🧠 Kaikun04 CTOレビュー|cto|open|execute_now|open|refined|open|0|dev/batch-2615-2615|https://github.com/douyo01-byte/openclaw-factory/pull/2339
2613|MotherShip: log cleanup|mothership|open|execute_now|open|decomposed|open|0|dev/mothership-log-clean-ca0604|https://github.com/douyo01-byte/openclaw-factory/pull/2351
2609|MotherShip: log cleanup|mothership|open|execute_now|open|decomposed|open|0|dev/mothership-log-clean-fd6d17|https://github.com/douyo01-byte/openclaw-factory/pull/2334
2599|MotherShip: db check|mothership|open|execute_now|open|decomposed|open|0|dev/mothership-db-check-8f855c|https://github.com/douyo01-byte/openclaw-factory/pull/2349
2575|MotherShip: log cleanup|mothership|open|execute_now|open|decomposed|open|0|dev/mothership-log-clean|https://github.com/douyo01-byte/openclaw-factory/pull/2352
2555|AI meeting improvement 2153 [phased]|ai_meeting_engine_v1|idea|backlog||raw||0|ai-meeting-20260314_215322|
2494|AI meeting improvement 1953 [phased]|ai_meeting_engine_v1|idea|backlog||raw||0|ai-meeting-20260314_195321|
2437|AI meeting improvement 1753 [phased]|ai_meeting_engine_v1|idea|backlog||raw||0|ai-meeting-20260314_175319|
2375|AI meeting improvement 1553 [phased]|ai_meeting_engine_v1|idea|backlog||raw||0|ai-meeting-20260314_155306|
2319|AI meeting improvement 1353 [phased]|ai_meeting_engine_v1|idea|backlog||raw||0|ai-meeting-20260314_135305|
2318|AI meeting improvement 1352 [phased]|ai_meeting_engine_v1|idea|backlog||raw||0|ai-meeting-20260314_135207|
2157|Reduce event summary drift in bots/company_dashboard_v1.py||throttled|execute_now|blocked_target_policy|refined||0|code-review/1773483250|
2103|Improve logging coverage in bots/ceo_help_v1.py||throttled|execute_now|blocked_target_policy|refined||0|code-review/1773477532|
2080|Strengthen launchd recovery in bots/ops_brain_v2.py||throttled|execute_now|blocked_target_policy|refined||0|code-review/1773475863|
1967|Reduce event summary drift in bots/chat_research_v1.py||throttled|execute_now|blocked_target_policy|refined||0|code-review/1773465545|
1867|Improve executor stability in bots/ops_brain_v1.py||throttled|execute_now|blocked_target_policy|refined||0|code-review/1773456200|
1850|Refactor duplicated logic in bots/browser_smoke.py||throttled|execute_now|blocked_target_policy|refined||0|code-review/1773455010|
1728|Reduce API latency in bots/report_orchestrator_v1.py||throttled|execute_now|blocked_target_policy|refined||0|code-review/1773444217|
1722|Improve lifecycle event safety in bots/openai_smoke.py||throttled|execute_now|blocked_target_policy|refined||0|code-review/1773443934|
1707|Reduce event summary drift in bots/explain_orchestrator_v1.py||throttled|execute_now|blocked_target_policy|refined||0|code-review/1773442998|
1703|Reduce API latency in bots/auto_pr_v1.py||throttled|execute_now|blocked_target_policy|refined||0|code-review/1773442732|
1685|Reduce duplicate writes in bots/auto_merge_v1.py||throttled|execute_now|blocked_target_policy|refined||0|code-review/1773441506|

```

## Kaikun02 runtime memo

```
# KAIKUN02 RUNTIME MEMO

## 事実
- 実働最小系は open_pr_guard_v1 / dev_pr_watcher_v1 / dev_pr_creator_v1
- open PR queue は現在 15
- duplicate open pr_url は 0
- dev_proposals が中核DB
- proposal_state は pending_question 列を期待する運用
- source_ai 空欄の旧履歴が残っている
- botファイル大量存在 = 本番稼働 ではない

## 今の本番判断
### 本番に近い
- open_pr_guard_v1
- dev_pr_watcher_v1
- dev_pr_creator_v1
- proposal_promoter_v1
- spec_refiner_v2
- spec_decomposer_v1

### 要監査
- innovation_engine_v1
- strategy_engine_v1
- proposal_builder_loop_v1
- reasoning_engine_v1
- proposal_throttle_engine_v1
- learning_result_writer_v1
- pattern_extractor_v1
- supply_bias_updater_v1

## producer再開条件
- unique open PR count <= 15
- duplicate open pr_url = 0
- closed / merged と pr_status の不整合増加なし
- creator / watcher / guard の3点が安定

## 毎回最初に見るSQL
select count(distinct pr_url)
from dev_proposals
where coalesce(pr_status,'')='open'
  and coalesce(pr_url,'')<>'';

select
  coalesce(source_ai,''), count(distinct pr_url)
from dev_proposals
where coalesce(pr_status,'')='open'
  and coalesce(pr_url,'')<>''
group by 1
order by 2 desc;

select count(*)
from (
  select pr_url
  from dev_proposals
  where coalesce(pr_status,'')='open'
    and coalesce(pr_url,'')<>''
  group by pr_url
  having count(*) > 1
);

```