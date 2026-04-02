# OpenClaw Bot Catalog

## 現行運用 LaunchAgent

- jp.openclaw.supervisor
- jp.openclaw.dev_command_executor_v1
- jp.openclaw.dev_pr_watcher_v1
- jp.openclaw.tg_poll_loop
- jp.openclaw.self_healing_v2
- jp.openclaw.spec_refiner_v2
- jp.openclaw.spec_reply_v1
- jp.openclaw.spec_notify_v1
- jp.openclaw.dev_proposal_notify_daemon_v1
- jp.openclaw.log_rotate_safe_v1
- jp.openclaw.ai_employee_manager_v1

## disable / 削除済み

- jp.openclaw.ingest_private_replies_v1
- jp.openclaw.dev_executor_daemon_v1
- jp.openclaw.auto_pr
- jp.openclaw.auto_pr_v2
- jp.openclaw.spec_executor_min_v1
- jp.openclaw.tg_private_ingest_v1

## broken退避対象

- jp.openclaw.ai_idea_generator_v1
- jp.openclaw.idea_promoter_v1
- jp.openclaw.project_decider
- jp.openclaw.project_decider_v2
- jp.openclaw.self_learning

## 実コード / 実ロジックあり

### factory主幹
- project_brain_v4
- llm_decider_v1
- learning_brain_v1
- executor_guard
- infra_brain
- business_brain
- market_brain
- revenue_brain
- self_improve

### daemon / I/O
- dev_command_executor_v1
- dev_pr_watcher_v1
- tg_poll_loop
- report_orchestrator_v1
- company_dashboard_v1
- ceo_help_v1
- spec_refiner_v2
- spec_reply_v1
- spec_notify_v1
- ai_employee_manager_v1

### 実コード確認済みファイル
- dev_executor_v1.py
- spec_refiner_v2.py
- chat_research_v1.py
- scout_market_v1.py
- scout_market_v2.py
- company_dashboard_v1.py
- ceo_help_v1.py
- meeting_orchestrator_v1.py
- employee_registry_v1.py
- dev_pr_watcher_v1.py
- bots/report_orchestrator_v1.py
- team/sakura_scout.py
- team/kenji_researcher.py

## 実稼働BOT

- Kaikun01
- Kaikun02
- Kaikun03
- SekawakuClaw

## 要確認 / 未完成

- watcher 全体の統合整理
- learning の評価軸
- self-healing の精度
- proposal供給ループ
- bots/research_brain
- bots/spec_engine
- bots/dev_engine

## 構想のみ / UI人格

- しらべえ
- さがすけ
- かんがえもん
- きめたろう
- つくるぞう
- みはるん
- くっつけ丸
- ひしょりん
- しらせるん
- とどけるん
- まわすけ
- なおし丸
- みはりん

## 補足

- 実在 = 完成ではない
- pycのみ確認のものは再構築候補として扱う
- UI人格は実コードBOTと分けて管理する
