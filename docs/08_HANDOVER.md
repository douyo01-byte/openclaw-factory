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

## 2026-03-26 追記: Kaikun02 routed残件

- Kaikun02 worker は現行 runtime に存在しない
- `task_router_v1` は `kaikun02` task を作るが、処理実行体は未接続
- 既存の `kaikun02 new` 残件は `skipped_no_kaikun02_worker` で整理済み
- 現時点で `router_tasks target_bot='kaikun02' and status='new'` は 0
- 今後 Kaikun02 を復活させるなら worker 実装または routed 抑止が必要


## 2026-03-26 追記 : finisher最終整合

- router_reply_finisher_v1 は送信成功時に sent_message_id を保存する
- inbox_commands は finisher成功で done / processed=1 / sent に揃う
- task 522 / inbox 474 で sent_message_id 永続化まで確認済み
- reply本流の未整合は解消済み


## 2026-03-26 追 記 : exec bridge

- `kaikun04_exec_bridge_v1` 追 加 済 み
- Kaikun04 done reply の `[EXEC]` を `ops_exec` child task に 変 換
- `self_improvement_log` で 親 子 関 係 を 記 録
- 確 認 済 み smoke : parent 538 -> child 539 -> `db_health.sh`
- 以 後 は Telegram 指 示 → Kaikun04 提 案 → 安 全 script 実 行 の 連 鎖 が 使 え る


## 2026-03-27 handover 追記

### 今回完了
- EXEC payload routing hardening を main 反映
- malformed EXEC payload の skip正規化を main 反映
- Kaikun04 worker completion 時の applied / router_task_id 反映を main 反映
- finisher safe_text を main 反映
- legacy secretary_done 残留を全件閉塞
- private/manual ともに pending / new 残なしを確認

### 現在の運用ルール
- `ops_exec` に流れるのは EXEC専用形のみ
- THINK/FAST本文に `[EXEC]` の語が含まれても即 ops_exec には行かない
- EXEC提案は Kaikun04 → exec_bridge → ops_exec の順で処理
- malformed EXEC は failed ではなく skip系で閉じる
- reply送信は finisher が担当し、長文は safe_text で切り詰める

### 次に見る場所
- `bots/task_router_v1.py`
- `bots/telegram_ops_executor_v1.py`
- `bots/kaikun04_router_worker_v1.py`
- `bots/router_reply_finisher_v1.py`

### 現在の健全性
- secretary_done_remaining = 0
- tg_private_pending = 0
- manual_pending = 0
- ops_exec_new_remaining = 0
- kaikun04_new_remaining = 0
- kaikun04_done_sent_missing = 0


## self_improvement_log lifecycle 拡張
- self_improvement_log に status / parent_reply_head / child_result_head / applied_at / updated_at を追加
- Kaikun04 exec bridge が queued / skipped を記録
- telegram_ops_executor_v1 が child ops_exec の done / failed / skipped を self_improvement_log に反映
- 検証: parent_task_id=550 -> child_task_id=551
- script=db_health.sh の child 実行完了まで self_improvement_log で追跡可能


## self_improvement learning bridge handover

- daemon main で self_improvement_to_learning_v1 を追加済み
- self_improvement_log done 行は learning_results に自動反映される
- live DB の learning_results schema は proposal_id 必須のため synthetic proposal_id 方式を採用
- 直近検証:
  - self_improvement_log id=2 -> learning_bridge_status=done
  - learning_result_id=3052
  - learning_results.proposal_id=-1000000002
- 次段は learning_results / self_improvement_log を pattern 化 or 改善ルール抽出へ接続すること


## 2026-03-27 self improvement feedback loop

- self_improvement_to_learning_v1 により self_improvement_log の完了行を learning_results へ橋渡し済み
- synthetic proposal_id は `-1000000000 - self_improvement_log.id`
- self_improvement_pattern_bridge_v1 により learning_results から learning_patterns / success_patterns へ反映済み
- pattern_type=`self_improvement_exec` の成功例:
  - script=db_health.sh
  - script=status_core.sh
- kaikun04_router_worker_v1 は learning_patterns を読み、health-check 系 THINK では強い成功パターンがある場合のみ allowlisted EXEC を末尾に 1つだけ自動付与
- EXEC は allowlisted script のみ許可し、非許可形式は normalize_exec_block で除去
- 直近確認:
  - secretary_done_remaining=0
  - tg_private_pending=0
  - manual_pending=0
  - ops_exec_new_remaining=0
  - kaikun04_new_remaining=0
  - kaikun04_done_sent_missing=0
