# OpenClaw Handover

## 前提

- この文書は最新の自動引き継ぎ
- 実ファイル・実DB・実ログ・実プロセスを優先
- 核ファイルは手動管理、状態ファイルは自動生成

## 今回の自動要約

- generated_at: 2026-03-10 00:01:41
- branch: dev/self-watch-recovery
- head: 03c4733
- db: /Users/doyopc/AI/openclaw-factory-daemon/data/openclaw_real.db

## 現在の本当の状態

### launchagents
- jp.openclaw.ai_ceo_engine: running
- jp.openclaw.ai_employee_factory: running
- jp.openclaw.ai_employee_manager_v1: running
- jp.openclaw.ai_meeting_engine: running
- jp.openclaw.business_engine: running
- jp.openclaw.ceo_dashboard: spawn scheduled
- jp.openclaw.code_review_engine: running
- jp.openclaw.dev_command_executor_v1: running
- jp.openclaw.dev_pr_automerge_v1: running
- jp.openclaw.dev_pr_watcher_v1: running
- jp.openclaw.docs_auto_snapshot: not running
- jp.openclaw.docs_sync_v1: running
- jp.openclaw.event_notify_v1: spawn scheduled
- jp.openclaw.innovation_engine: running
- jp.openclaw.log_rotate_safe_v1: not running
- jp.openclaw.revenue_engine: running
- jp.openclaw.self_healing_v2: running
- jp.openclaw.self_repair_engine: running
- jp.openclaw.spec_notify_v1: running
- jp.openclaw.spec_refiner_v2: running
- jp.openclaw.spec_reply_v1: running
- jp.openclaw.supervisor: running
- jp.openclaw.tg_poll_loop: running
- jp.openclaw.update_pr_created: running

### dev_proposals
- approved: 4
- archived: 152
- closed: 198
- hold: 61
- idea: 1
- merged: 455
- open: 1

### proposal_state
- closed: 2
- merged: 61
- pr_created: 1
- refined: 4

### ceo_hub_events
- ai_employee: 6
- learning_result: 79
- merged: 125
- pr_created: 75
- revenue: 5

### latest proposals
- 993 | Improve logging coverage in dev_autogen/p52.txt | merged
- 992 | PR5 ORDER TEST | merged
- 991 | RANK TEST HIGH | merged
- 990 | RANK TEST MID | merged
- 989 | RANK TEST LOW | merged
- 988 | Optimize database queries in dev_autogen/p402.txt | merged
- 987 | Improve logging coverage in dev_autogen/p134.txt | merged
- 986 | BATCH TEST C | merged
- 985 | BATCH TEST B | merged
- 984 | BATCH TEST A | merged

## 確認できた重要事項

- 非核 docs は自動同期対象
- 主幹 active pipeline の DB は daemon real db へ統一済み
- 会社状態表示は live DB と一致する方向に修正済み

## 次チャットで最初に打つコマンド

cd ~/AI/openclaw-factory-daemon || exit 1

## 次に見る項目

1. tg_poll_loop の会社状態表示が live 値と一致しているか
2. docs/06_CURRENT_STATE.md と docs/08_HANDOVER.md の自動生成内容が十分か
3. .bak / archive をどこまで整理するか
