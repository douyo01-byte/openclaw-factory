# OpenClaw Handover

## 最初に見るもの
1. docs/06_CURRENT_STATE.md
2. docs/10_RUNTIME_AUDIT_STATUS.md
3. docs/04_KAIKUN04_STARTER.md

## 今の判断

- 現役ACTIVE本流は promoted tuning observability runtime live 本流まで接続済み
- proposal 3285 は observability_runtime_live_review_only 到達済み
- private reply 本流は healthy
- cluster bias は stable
- watcher は 24h で watch ログのみ、再起動 / エスカレーション / 通知 / proposal なし
- docs旧記述より live DB / live logs / launchctl / watcher 結果を優先する

## 次の行動

- ACTIVE本流テンプレをこの状態で維持
- watcher 詳細は ops_watcher_events 実スキーマ準拠で読む
- target 列前提の旧SQLは使わない
- 長時間監視の結果整理を docs/10_RUNTIME_AUDIT_STATUS.md 側へ寄せる

## 監視メモ

- required:
  - jp.openclaw.ops_brain_agent_v1
  - jp.openclaw.private_reply_to_inbox_v1
  - jp.openclaw.secretary_llm_v1
- observe:
  - jp.openclaw.dev_pr_automerge_v1
  - jp.openclaw.db_integrity_watchdog_v1
  - jp.openclaw.kaikun02_coo_controller_v1
  - jp.openclaw.dev_pr_watcher_v1
  - jp.openclaw.ingest_private_replies_kaikun04
