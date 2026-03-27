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


## 2026-03-26 追記 : router finisher sent_message_id 永続化

完了
- router_reply_finisher_v1 で Telegram送信成功時に router_tasks.sent_message_id を保存するよう修正
- inbox_commands も finisher 成功時に done / processed=1 / sent へ更新するよう統一
- task 522 で sent_message_id=398 保存を実地確認
- Kaikun04 reply 本流は DB整合込みでクローズ済み

現状態
- kaikun04_done_sent_missing = 0
- kaikun02_new_remaining = 0
- private_pending = 0


## 2026-03-26 追 記 : Kaikun04 exec bridge 本 流

完 了
- Kaikun04 reply 末 尾 の `[EXEC]` を  bridge し て `ops_exec` child task 化 す る `kaikun04_exec_bridge_v1` を 追 加
- `telegram_ops_executor_v1` と 接 続 し 、 allowlisted script 実 行 結 果 を Telegram 返 却 で き る 状 態 に 到 達
- `self_improvement_log` を 追 加 し 、 parent -> child の 実 行 連 鎖 を 記 録
- manual smoke で parent task 538 -> child task 539 -> `db_health.sh` 実 行 成 功 を 確 認

現 状 態
- Kaikun04 は 回 答 末 尾 に safe allowlisted `[EXEC]` を 出 せ る
- exec bridge -> ops_exec -> finisher の 最 小 自 己 改 善 ル ー プ は 稼 働


## 2026-03-27 追記: EXECルーティング硬化と残留閉塞の完了

- task_router_v1 は EXEC専用payloadのみ `ops_exec` へ送るよう硬化済み
- THINK本文中に `[EXEC]` という語が含まれるだけでは `ops_exec` に誤ルーティングされない
- telegram_ops_executor_v1 は malformed EXEC payload を `skipped_bad_exec_payload` で正規化して閉じる
- Kaikun04 worker は reply生成完了時に `inbox_commands.router_finish_status='applied'` と `router_task_id` を自動反映
- finisher は送信前に safe_text で長文を丸めて Telegram 400 を回避
- legacy `secretary_done` 残留はすべて閉塞済み

### 2026-03-27 現在の確認値
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


## self_improvement_to_learning_v1 追加

- self_improvement_log の done 行を learning_results に橋渡しする mainline を追加
- live schema に合わせて learning_results へ挿入する列を動的選択
- synthetic proposal_id を使って self improvement 系 learning を永続化
- 検証済み:
  - self_improvement_log id=2
  - parent=550 -> child=551
  - learning_result_id=3052
  - proposal_id=-1000000002


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


## 2026-03-27 self improvement skipped rows learning bridge
- self_improvement_to_learning_v1 が skipped 行も learning_results に反映する構成へ更新
- skipped 事例も synthetic proposal_id で learning_results に保存
- 検証対象:
  - self_improvement_log id=3 -> proposal_id=-1000000003
  - self_improvement_log id=4 -> proposal_id=-1000000004
- done / skipped の両方が self_improvement -> learning に残る状態へ統一
