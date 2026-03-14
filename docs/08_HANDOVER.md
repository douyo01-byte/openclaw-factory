
---

## 2026-03-14 追加更新: CEO decision layer 接続後の最新本流

### 正本DB

正本DBは `~/AI/openclaw-factory/data/openclaw.db` を使用する。  
`openclaw_real.db` と `openclaw_daemon.db` は本流DBではない。

### 最新本流pipeline

brain_supply
→ proposal_dedupe
→ dev_router
→ spec_refiner_v2
→ dev_command_executor / dev_executor
→ dev_pr_creator
→ dev_pr_watcher
→ dev_pr_automerge
→ dev_merge_notify
→ impact_judge
→ learning_result_writer
→ pattern_extractor
→ proposal_cluster
→ supply_bias_updater
→ self_improvement_engine_v2
→ ceo_hub_sender
→ ceo_priority_scorer
→ ceo_decision_layer_v1
→ ai_meeting_engine_v1
→ command_apply_daemon
→ executor

### 本流active

- brain_supply_v1
- proposal_dedupe_v1
- dev_router_v1
- spec_refiner_v2
- dev_command_executor_v1
- dev_executor_v1
- dev_pr_creator_v1
- dev_pr_watcher_v1
- dev_pr_automerge_v1
- dev_merge_notify_v1
- impact_judge_v1
- learning_result_writer_v1
- pattern_extractor_v1
- proposal_cluster_v1
- supply_bias_updater_v1
- self_improvement_engine_v2
- ceo_hub_sender_v1
- ceo_priority_scorer_v1
- ceo_decision_layer_v1
- command_apply_daemon_v1

### support

- healthcheck_v1
- db_integrity_check_v1
- schema_guardian_v1
- schema_migration_engine_v1
- executor_guard_v2
- executor_audit_v1
- self_healing_v2
- self_strength_watchdog_v1
- secretary_llm_v1
- meeting_orchestrator_v1
- dev_meeting_telegram_bridge_v1
- tg_poll_loop
- spec_reply_v1
- spec_notify_v1
- ingest_private_chat_v1
- cto_review_v1

### active-support 境界

- ai_meeting_engine_v1

理由:
CEO decision layer と接続済みで、meeting_needed=1 の proposal から ai_meeting proposal を自動生成できる状態になった。  
ただし現時点では会議結果を元proposalの decision summary へ戻す処理は未実装。

### 実装済み追加事項

- `ceo_decision_layer_v1.py` を追加
- `proposal_ranking_v1.py` の priority を CEO decision layer へ接続
- `ai_meeting_engine_v1.py` を `meeting_needed=1` ベースへ接続
- `ai_meeting_engine_v1.py` の proposal insert に `branch_name` と `source_ai=ai_meeting_engine_v1` を追加
- `ai_meeting` proposal 自動生成成功
- `ceo_hub_events` に `event_type='ai_meeting'` を proposal_id 付きで登録成功

### 反映済みコミット

- openclaw-factory-daemon
- commit: `04e1911`
- message: `Add CEO decision layer and connect proposal ranking + AI meeting`

### 次の最優先

1. ai_meeting の結果を ceo_decision_layer_results.summary に戻す
2. 元proposal と ai_meeting proposal の対応づけを明文化する
3. 文字間スペース崩れのある handover 記述を後で整形する
4. backup / .bak ファイル群は後で整理する

