# OpenClaw Operations

## 常駐運用メモ

1. enabled と running は別
2. launchctl に見えても内部ロジックが止まっていることがある
3. tg_poll_loop.sh は現役ファイルを毎回確認
4. 1行崩れで複数コマンドが潰れることがある
5. while true 内に sleep があるか確認
6. pgrep は PID だけでなく何が走っているかも見る
7. queue に update が残っているのに DB に入らない時は ingest を疑う
8. DBに入って done なのに実返信がない時は送信側を疑う
9. 手動実行で直るなら env / loop / launch の問題を疑う
10. 手動でも動かないなら本体ロジックを疑う

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

## 個別補足

### tg_poll_loop.sh
- 稼働中
- Telegram polling
- CEO command
- report_orchestrator 実行
- ingest_telegram_replies / report_orchestrator / sleep を含む

### report_orchestrator_v1
- bots/report_orchestrator_v1.py
- LaunchAgent直起動ではない
- scripts/tg_poll_loop.sh から起動
- 600秒周期
- ceo_hub_events →レポート生成→ Telegram送信

### auto_meet_loop.sh
- 未運用
- または構想段階
- 実運用では使用されていない

## 現在の運用上の課題

1. proposal供給量
2. learning評価軸
3. CEOダッシュボード精度
4. LaunchAgent の現役 / 残骸整理
5. archive候補の段階的隔離

## スマホ貼り付け時の注意

- スマホからターミナルへ長文を貼ると、日本語の文字間に空白が混入することがある
- docs をスマホ経由で更新した日は、最後に必ず spacing 修正を実行する
- 確認対象はまず docs/01_SYSTEM_PROMPT.md

実行コマンド:
python scripts/fix_docs_spacing.py

確認コマンド:
sed -n '1,20p' docs/01_SYSTEM_PROMPT.md