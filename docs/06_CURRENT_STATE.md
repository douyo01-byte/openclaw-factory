# OpenClaw Current State

## 現在の正
- docs単体ではなく docs / DB / runtime 一致状態を正とする
- watcher判定は `~/AI/openclaw-factory-daemon/scripts/check_watcher_health_24h.py` を使う
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

## live status
- watcher 24h:
  - restarted=0
  - escalations=0
  - notifications=0
  - proposals=0
- health judgement:
  - OK: no restart/escalation/notification/proposal in 24h
  - OK: all required services running

## DB path
- canonical:
  - `~/AI/openclaw-factory/data/openclaw.db`
- daemon link:
  - `~/AI/openclaw-factory-daemon/data/openclaw.db`
  - `-> ~/AI/openclaw-factory/data/openclaw.db`

## runtime実体
- `jp.openclaw.ops_brain_agent_v1`
  - `~/AI/openclaw-factory/scripts/run_ops_brain_agent.sh`
- `jp.openclaw.private_reply_to_inbox_v1`
  - `~/AI/openclaw-factory-daemon/scripts/run_private_reply_to_inbox_v1.sh`
- `jp.openclaw.secretary_llm_v1`
  - LaunchAgent上の `program=/bin/zsh`

## 2026-03-26 Kaikun04 reply mainline 復旧

完了
- Kaikun04 router worker / router reply finisher の env 読み込み安定化
- private reply -> inbox -> task_router -> kaikun04 worker -> finisher の本流復旧
- task 514 / 519 で Kaikun04 が実回答を返すことを確認
- inbox_commands 466 / 471 は routed -> sent を確認
- sent_message_id 欠損は backfill_from_sent_state で整合化
- PR #2705 を squash merge 済み
- daemon main 最新同期済み

現状態
- Kaikun04 はオウム返しではなく実回答を返す
- private -> router -> worker -> finisher の reply 本流は完全クローズ
- daemon main: f974d15

## 2026-03-26 追記: Kaikun02 routed残件整理

完了
- Kaikun02 worker 不在を runtime / LaunchAgents / router_tasks で確認
- routed 後に `target_bot='kaikun02'` のまま `status='new'` で滞留していた残件を棚卸し
- 残件は `skipped_no_kaikun02_worker` で整合化
- `router_tasks target_bot='kaikun02' and status='new'` は 0 を確認

現状態
- Kaikun04 reply 本流は復旧済み
- Kaikun02 は worker 不在のため routed 後は自動実行しない
- 古い routed 残件は DB 上でクローズ済み
