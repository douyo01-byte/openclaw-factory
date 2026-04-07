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


## 2026-03-27 self improvement skipped rows learning bridge
- self_improvement_to_learning_v1 が skipped 行も learning_results に反映する構成へ更新
- skipped 事例も synthetic proposal_id で learning_results に保存
- 検証対象:
 - self_improvement_log id=3 -> proposal_id=-1000000003
 - self_improvement_log id=4 -> proposal_id=-1000000004
- done / skipped の両方が self_improvement -> learning に残る状態へ統一


## 2026-03-27 引き継ぎ追記（skipped learning bridge fix）

### 反映済み
- PR #2731 `Include skipped self improvement rows in learning bridge`
- `bots/self_improvement_to_learning_v1.py` の fetch 条件を
 - `coalesce(status,'')='done'`
 から
 - `coalesce(status,'') in ('done','skipped')`
 へ修正

### 実結果
- skipped の self_improvement_log 行も learning_results に記録されるようになった
- 確認済み:
 - id=3 -> proposal_id=-1000000003 -> result_type=skipped
 - id=4 -> proposal_id=-1000000004 -> result_type=skipped
- 負例 `no_exec_block` が learning_patterns に蓄積される状態まで閉じた

### 現在の自己改善ループ
Kaikun04 THINK
-> exec_bridge
-> ops_exec child
-> self_improvement_log
-> learning_results
-> learning_patterns / success_patterns
-> Kaikun04 prompt feedback
まで全て接続済み

### 現在の運用上の見方
- 成功 EXEC は `self_improvement_exec` として再利用候補になる
- skipped/no_exec_block は負例として残る
- Kaikun04 auto EXEC は allowlist + 強パターンのみで保守的に付与される


## 2026-03-27 self improvement negative feedback 反映

- Kaikun04 への自己改善フィードバックに negative EXEC pattern を追加
- `learning_patterns.pattern_type='self_improvement_exec'` の weight<=0 パターンも prompt へ反映
- 現在の negative 代表例:
 - `no_exec_block` weight=0.000 success=0/2
- positive pattern と negative pattern を同時に見せることで、
 EXEC を出すべきでないケースを学習済み知見として抑制
- allowlisted EXEC 制約は維持
- worker 再起動確認済み

確認値
- secretary_done_remaining=0
- tg_private_pending=0
- manual_pending=0
- ops_exec_new_remaining=0
- kaikun04_new_remaining=0
- kaikun04_done_sent_missing=0


## 2026-03-27 self_improvement_feedback_metrics_v1

追加:
- self_improvement_feedback_metrics_v1 を追加
- self improvement -> learning -> pattern ループの状態を obs/self_improvement_feedback.json へ定期出力
- 正の EXEC パターンと負の no_exec_block パターンを 1ファイルで確認可能

確認済み:
- self_improvement_log_total=6
- done_rows=3
- skipped_rows=2
- learning_done_rows=5
- pattern_done_rows=5
- negative_learning_rows=2
- positive_learning_rows=3
- secretary_done_remaining=0
- tg_private_pending=0
- manual_pending=0
- ops_exec_new_remaining=0
- kaikun04_new_remaining=0
- kaikun04_done_sent_missing=0

主要パターン:
- script=status_core.sh
- script=db_health.sh
- no_exec_block

## 2026-03-27 追記 : feedback summary Telegram送信確認 完了
### 完了
- `scripts/tg_poll_loop.sh` の `DB_PATH` / `FACTORY_DB_PATH` を `~/AI/openclaw-factory/data/openclaw.db` に統一
- `tg_poll_loop.sh` は `~/AI/openclaw-factory/env/openai.env` 不在でも落ちないよう修正
- `jp.openclaw.tg_poll_loop` を再起動し、`state=running` / `last exit code=(never exited)` を確認
- heartbeat 再開を確認
- `ceo_hub_sender_v1` の自動送信再開を確認
- `ceo_hub_events.id=35433` を指定送信し、`sent_at=2026-03-27 20:13:46` 更新を確認
- 実送信本文に以下を確認
 - `【 自 己 改 善 】 正 3 / 負 2`
 - `【 EXEC 学 習 】 成 功 script=status_core.sh / 抑 制 no_exec_block x2`
 - `【 ル ー プ 健 康 】 private=0 ops_exec=0 kaikun04=0`

### 現在の意味
- self improvement feedback loop は 生成 -> DB投入 -> CEO Telegram共有 まで閉じた
- 残タスクだった Kaikun02 / CEO送信面の最終確認は完了

## 2026-04-02 docs再構築

### 完了
- 欠損していた core docs を git history から復旧
 - 01_SYSTEM_PROMPT
 - 17_EFFICIENCY_RULES
 - 20_DAILY_OPERATION
 - 02_MASTER_PLAN
 - 07_ROADMAP
- priority docs を reference_recovered に集約
- 03_SYSTEM_OVERVIEW を新規作成
- docs構造を Core / Rules / Reference に整理
- Anti-loss rule を policy に追加
- docsとgitの乖離検出フローを確立

### 現在地
- docsは「欠損なし状態」へ復旧完了
- reference系は隔離済み
- INDEXベース運用へ移行済み

### 次
- docs / runtime / DB の完全一致チェック
- reference → core昇格候補の選定

## 2026-04-02 docs/runtime/db 一致確認

### 完了
- docs integrity checker 実行で RESULT: OK を確認
- watcher 24h 健全性確認
- required 3 targets running 確認
- daemon DB symlink 確認
- router health 0残件確認

### 現在地
- OpenClaw 本流は健全
- manual backlog が 14 件残っている
- secretary_done_remaining = 0
- tg_private_pending = 0
- ops_exec_new_remaining = 0
- kaikun04_new_remaining = 0
- kaikun04_done_sent_missing = 0

### 次
- manual_pending 14件の内訳確認
- 閉じてよい残件か、未処理依頼かを判定

## 2026-04-02 handover 追記: direct EXEC primary 化 完了
- Kaikun04 は EXEC 提案だけでなく direct child task 作成まで担当
- 検証済み:
 - parent task 565 -> child task 566
 - 565: `exec_bridge_status='direct'`, `exec_child_task_id=566`
 - 566: `ops_exec done`
 - self_improvement_log latest: `kind='exec_direct'`, `status='done'`
- `kaikun04_exec_bridge_v1` は fallback 条件へ変更済み
 - `coalesce(exec_bridge_status,'')=''`
 - `coalesce(exec_child_task_id,0)=0`
- これにより direct EXEC が primary、exec_bridge は fallback へ移行
- `scripts/run_kaikun04_exec_bridge_v1.sh` を追加し LaunchAgent 起動欠損も解消

## 2026-04-02 handover 追記: routing 判断の Kaikun 集約
- task_router_v1 は `target='kaikun04'` 固定の入口へ簡素化
- `mode` も task_router では付与しない構成へ変更
- 実質的な mode / exec 判断は Kaikun04 worker 側に集約される
- 次段は Kaikun04 内で THINK / FAST / DOC / EXEC の判断ルールを明文化すること

## 2026-04-02 handover 追記: Kaikun decision layer
- Kaikun04 worker 側で mode 判断を持つ構成へ移行
- 判断種別:
 - DOC
 - THINK
 - EXEC
 - CHAT
- EXEC は policy で制御:
 - auto
 - confirm
 - deny
- 次段は `decide_mode()` と `decide_exec_policy()` の精度を上げること

## 2026-04-02 handover 追記: cleanup 完了
- 旧 failed router_tasks を削除
- routed/new の残件を skipped 化
- 動作上の本線は成立済みとして次段へ進む
- 次フェーズは OSS統合設計（OpenClaude / n8n / agent orchestration）

## 2026-04-02 handover 追記: exec provider abstraction
- `ops_exec` をローカル固定実行から provider 抽象化へ変更
- provider:
 - local
 - openclaude (simulation)
- 次段は `run_openclaude()` を実API/CLI接続へ差し替えること

## 2026-04-02 handover 追記: n8n 修復優先
- 収益化より先に基盤強化を優先
- n8n は npm 版ではなく Colima + Docker で復旧する
- 次段は n8n 起動確認後、OpenClaw との最小連携を作る

## 2026-04-03 handover 追記: n8n mainline established
- n8n は Colima + Docker で復旧済み
- Webhook -> HTTP Request -> api_server.py -> inbox_commands の最小構成を確立
- n8n source の task が task_router を通って kaikun04 / ops_exec まで完走
- telegram_ops_executor_v1 は launch script で DB_PATH を固定して安定化
- 次段は api_server.py の常駐化と n8n workflow の正式固定

## 2026-04-03 handover 追記: stabilization finalized
- n8n mainline は修復ではなく運用状態へ移行
- api_server は LaunchAgent 管理へ統一
- executor / router / kaikun04 の mainline は安定
- 次段は Telegram 入口統合と運用設計

## 2026-04-03 handover 追記: Telegram entrance preparation
- primary entrance:
  Telegram -> n8n -> api_server -> inbox_commands
- fallback entrance:
  private_reply_to_inbox_v1 / manual insert
- 次段は n8n 側 JSON を `source` + `text` に統一し Telegram入口を寄せること

## 2026-04-03 handover 追記: Telegram primary established
- Telegram 入口は n8n 経由を primary とする方針を runtime でも確認
- スマホから Tailscale 経由で n8n に入れる状態を確認
- n8n は `~/.n8n` bind mount で永続化
- fallback entrance は private_reply_to_inbox_v1 / manual insert を維持
- 次段は Telegram 直結ルートとの整理と運用ルール固定

## 2026-04-03 handover 追記: route role split
- primary:
  Telegram -> n8n -> api_server -> inbox_commands -> task_router -> kaikun04
- fallback:
  private_reply_to_inbox_v1 / ingest_private_replies_kaikun04 / manual insert
- secretary_llm_v1 は primary から外し、legacy / fallback 扱いで維持
- 次段は LaunchAgent の required / observe / fallback 整理と Telegram直結ルート縮退方針

## 2026-04-03 handover 追記: primary burn-in confirmed
- `telegram_n8n` source の追加確認でも primary route 完走
- 555 -> 618 -> 619 で end-to-end を確認
- secretary_llm_v1 は停止せず維持するが、運用上は legacy / fallback 扱い
- 次段は fallback の縮退方針と、必要なら secretary 系 LaunchAgent の observe 化

## 2026-04-03 handover 追記: fallback reduction candidate
- secretary_llm_v1 は legacy / fallback のまま維持しつつ observe candidate として扱う
- private reply 系は emergency fallback として残す
- 次段は primary burn-in を伸ばした上で fallback の縮退可否を判断

## 2026-04-03 handover 追記: fallback status clarified
- private_reply_to_inbox_v1 は DB env 汚染除去後に正常待機を確認
- usable fallback:
  private_reply_to_inbox_v1 / manual insert
- legacy fallback:
  ingest_private_replies_kaikun04 / secretary_llm_v1
- ingest_private_replies_kaikun04 は名前と実体にズレあり
- 次段は legacy fallback の命名整理 or observe 化

## 2026-04-03 handover 追記: operational classification fixed
- primary / usable fallback / legacy fallback の分類を固定
- 今は停止や削除よりも運用分類の固定を優先
- 次段は ingest_private_replies_kaikun04 の命名整理、または legacy の observe 扱い固定

## 2026-04-03 handover 追記: telegram route runtime check added
- `check_telegram_route_runtime.sh` を日常確認コマンドとして追加
- 次チャット開始時は runtime doc を読むだけでなく、このスクリプト実行から入ると状態把握が速い

## 2026-04-03 handover 追 記 : legacy fallback naming fixed
- `jp.openclaw.ingest_private_replies_kaikun04` は 名前 と 実 体 に ズ レ が あ る
- 実 体 は `bots/ingest_private_replies_v1.py`
- 今 は rename よ り も role の 固 定 を 優 先
- 次 段 で rename す る 場 合 も primary burn-in 後 に 行 う

## 2026-04-05 EXECライン安定化
- executor stability 修正を branch `chore/telegram-runtime-isolation` へ push 済み
- EXEC HEALTH レポートを ceo_hub_events へ送信可能
- 現在のEXEC集計は success 86 / failed 0 / skipped 2 / rate 97.7%
- stale started 回収あり、ops_exec 滞留なし

## 2026-04-07 repair chain / orchestrator 修復
- capability_watchdog_healer_v1 を導入
- capability_registry_builder_v1 に heal overlay を導入
- capability_watchdog_log を再計算し、healed を normal 判定へ反映
- capability_watchdog_repair_chain_summary_reporter_v1 に HEALED_NOW を追加
- capability_watchdog_repair_chain_planner_v1 で healed 済み capability の再起票を停止
- kaikun04_orchestrator_planner_v1 で repair capability 系を direct improve 1段で処理できる状態まで修正
- 古い repair capability 履歴は削除せず `[HISTORICAL_REPAIR_NOISE]` を付与して識別可能化
- 古い `no_orchestrator_match` は `historical_no_orchestrator_match` に変更
- 最新の正常 repair 履歴は 2081 / 2082 として維持

### 現在の本当の状態
- self_evolution:6 = normal / healed / score=1.0 / success=1 / failure=1
- self_evolution:13 = normal / healed / score=1.0 / success=1 / failure=1
- REPAIR_CHAIN_SUMMARY の BAD_HEALTH_NOW は空
- HEALED_NOW に healed 2件が表示される
- repair chain planner は新規 repair task を追加していない

### DB確認
- capability_watchdog_log
- capability_watchdog_heal_log
- capability_watchdog_repair_chain_log
- capability_registry
- kaikun04_orchestrator_plan_log
- kaikun04_orchestrator_stage_log

### 注意点
- 過去の repair capability task 履歴は router_tasks に残っている
- no_orchestrator_match の古い記録は履歴として残存
- 既存履歴の整理は未実施だったが、識別可能化までは完了

