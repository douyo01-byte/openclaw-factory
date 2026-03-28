# DB WRITE MAINTENANCE RULES

## 目的
SQLite の手動 cleanup や artifact 整理を行うとき、DB writer を一時停止して lock を避ける。

## 一時停止対象
- jp.openclaw.tg_poll_loop
- jp.openclaw.private_reply_to_inbox_v1
- jp.openclaw.router_reply_finisher_v1
- jp.openclaw.telegram_os_outbox_sender_v1
- jp.openclaw.self_improvement_to_learning_v1
- jp.openclaw.self_improvement_pattern_bridge_v1
- jp.openclaw.self_improvement_feedback_metrics_v1
- jp.openclaw.ingest_private_replies_kaikun04
- jp.openclaw.telegram_ops_executor_v1
- jp.openclaw.kaikun04_router_worker_v1
- jp.openclaw.telegram_os_creative_pipeline_v1

## 停止しなくてよいもの
- jp.openclaw.secretary_llm_v1
- jp.openclaw.ops_brain_agent_v1
- jp.openclaw.business_sample_watcher_v1
- jp.openclaw.task_router_v1
- jp.openclaw.kaikun04_exec_bridge_v1

## 手順
1. ./scripts/maintenance_db_write_pause.sh
2. sqlite3 で cleanup 実行
3. ./scripts/maintenance_db_write_resume.sh

## 確認
- lsof "$DB_PATH" "$DB_PATH-wal"
- launchctl list | grep '^.*jp\.openclaw\.'

## job19 現行正本
- lp_html_export_v3 version=39
- public_preview_url 最新1件
