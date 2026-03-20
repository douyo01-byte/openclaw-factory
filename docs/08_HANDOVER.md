# OpenClaw Handover

## 前提
- 実ファイル・実DB・実ログ・実process を docs より優先する
- docs は現状把握の補助、最終判断は runtime 実態で行う

## 最初に見るもの
1. docs/06_CURRENT_STATE.md
2. docs/12_RUNTIME_CLASSIFICATION.md
3. ../openclaw-factory/data/openclaw.db の live 状態
4. ../openclaw-factory-daemon の launchctl 実態
5. ops_watcher_events / ceo_hub_events の最新行

## 現在の本当の状態
- source of truth DB: /Users/doyopc/AI/openclaw-factory/data/openclaw.db
- open_pr: 0
- watcher required は jp.openclaw.ops_brain_agent_v1
- watcher observe stopped:
  - jp.openclaw.dev_pr_automerge_v1
  - jp.openclaw.db_integrity_watchdog_v1
  - jp.openclaw.kaikun02_coo_controller_v1
- proposal → PR → merged → executor_audit の本線は稼働中

## 次チャットで最初に打つコマンド
cd ~/AI/openclaw-factory-daemon || exit 1

## 次に確認する項目
1. openclaw.db の件数
2. ceo_hub_events 最新行
3. ops_watcher_events 最新行
4. watcher の required / observe 対象
5. legacy launchagent の棚卸し
- Meta HOLD 裁定完了: db_integrity_watchdog_v1 のみ保持、他は FULL_RETIRE 判定
- Business HOLD 裁定中 : scout_market_v2 / chat_research_v1 は MAINLINE_INTEGRATION_CANDIDATE、ai_employee_* は FULL_RETIRE、chat_research_job_producer_v1 / secretary_llm_v1 は再確認 HOLD
- Business HOLD 裁定完了 : scout_market_v2 / chat_research_v1 は MAINLINE_INTEGRATION_CANDIDATE、chat_research_job_producer_v1 / secretary_llm_v1 / ai_employee_* は FULL_RETIRE
