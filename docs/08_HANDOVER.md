# OpenClaw Handover

## 最初に見るもの
1. docs/06_CURRENT_STATE.md
2. docs/10_RUNTIME_AUDIT_STATUS.md
3. docs/08_HANDOVER.md
4. docs/11_OPERATIONS.md

## 現在の正
- docs単体ではなく docs / DB / runtime 一致状態を正とする
- runtime確認は watcher 24h health check を最優先で使う
- watcher は `ops_watcher_events.body` の JSON を唯一のソースとして扱う
- `ops_watcher_events` スキーマは `id / kind / body / created_at`
- private reply 本流は `Telegram -> tg_private_chat_log -> inbox_commands -> secretary_done`

## required targets
- `jp.openclaw.ops_brain_agent_v1`
- `jp.openclaw.private_reply_to_inbox_v1`
- `jp.openclaw.secretary_llm_v1`

## observe targets
- `jp.openclaw.dev_pr_watcher_v1`
- `jp.openclaw.ingest_private_replies_kaikun04`
- `jp.openclaw.db_integrity_watchdog_v1`
- `jp.openclaw.dev_pr_automerge_v1`
- `jp.openclaw.kaikun02_coo_controller_v1`

## 現在のruntime実体
- `jp.openclaw.ops_brain_agent_v1`
  - `~/AI/openclaw-factory/scripts/run_ops_brain_agent.sh`
- `jp.openclaw.private_reply_to_inbox_v1`
  - `~/AI/openclaw-factory-daemon/scripts/run_private_reply_to_inbox_v1.sh`
- `jp.openclaw.secretary_llm_v1`
  - LaunchAgent上の `program=/bin/zsh`

## DB
- daemon側DBは以下へ統一
- `~/AI/openclaw-factory-daemon/data/openclaw.db`
- `-> ~/AI/openclaw-factory/data/openclaw.db`

## 直近確認済み状態
- watcher 24h:
  - restarted=0
  - escalations=0
  - notifications=0
  - proposals=0
- required 3 targets running
- DB handle は 78 -> 6 まで削減済み

## 次の行動
- `python3 scripts/check_watcher_health_24h.py` を固定確認手順として使う
- required / observe / docs / runtime のズレのみ修正する
- 新規機能追加はしない

## 2026-03-26 追記: Kaikun04 reply mainline

- Kaikun04 reply 本流は完全クローズ
- private -> router -> worker -> finisher まで成立
- task 514 / 519 実回答確認済み
- inbox_commands 466 / 471 routed -> sent 確認済み
- sent_message_id 欠損は backfill_from_sent_state で整合化済み
- daemon main: f974d15
- PR #2705 merge 済み
