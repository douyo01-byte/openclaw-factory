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
- Kaikun04 reply 末 尾 の `[EXEC]` を bridge し て `ops_exec` child task 化 す る `kaikun04_exec_bridge_v1` を 追 加
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


## 2026-03-27 追加更新（skipped learning bridge 実装修正）

- self_improvement_to_learning_v1 は `status in ('done','skipped')` を対象に修正済み
- これにより skipped 行も learning_results へ正しく流入
- 検証済み:
 - self_improvement_log id=3 -> learning_bridge_status=done, learning_result_id=3055
 - self_improvement_log id=4 -> learning_bridge_status=done, learning_result_id=3056
 - learning_results proposal_id=-1000000003 / -1000000004 を確認
- learning_patterns:
 - `script=status_core.sh` sample=2 success=2 weight=1.0
 - `script=db_health.sh` sample=1 success=1 weight=1.0
 - `no_exec_block` sample=2 success=0 weight=0.0
- 健康状態:
 - secretary_done_remaining=0
 - tg_private_pending=0
 - manual_pending=0
 - ops_exec_new_remaining=0
 - kaikun04_new_remaining=0
 - kaikun04_done_sent_missing=0


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
- `scripts/tg_poll_loop.sh` の `DB_PATH` / `FACTORY_DB_PATH` を `~/AI/openclaw-factory/data/openclaw.db` に統一
- `tg_poll_loop.sh` は `~/AI/openclaw-factory/env/openai.env` 不在でも起動継続するよう修正
- `jp.openclaw.tg_poll_loop` を再起動し、`state=running` / `last exit code=(never exited)` を確認
- heartbeat 再開を確認
- `ceo_hub_sender_v1` の自動送信再開を確認
- `ceo_hub_events.id=35433` を指定送信し、`sent_at=2026-03-27 20:13:46` 更新を確認
- 実送信本文に以下を確認
 - `【 自 己 改 善 】 正 3 / 負 2`
 - `【 EXEC 学 習 】 成 功 script=status_core.sh / 抑 制 no_exec_block x2`
 - `【 ル ー プ 健 康 】 private=0 ops_exec=0 kaikun04=0`

意 味
- self improvement feedback loop は `ceo_hub_events` 投入だけでなく CEO Telegram共有まで閉じた
- 残タスクだった Kaikun02 / CEO送信面の最終確認は完了

## 2026-04-02 docs/runtime/db 一致確認
- docs integrity: OK
- watcher 24h: restarted=0 / escalations=0 / notifications=0 / proposals=0
- required 3 targets running を確認
- daemon DB symlink は canonical DB を指すことを確認
- router health:
 - ops_exec_new_remaining = 0
 - kaikun04_new_remaining = 0
 - kaikun04_done_sent_missing = 0
- inbox health:
 - secretary_done_remaining = 0
 - tg_private_pending = 0
 - manual_pending = 14
- 現状は mainline 健全、manual backlog のみ残存

## 2026-04-02 direct EXEC primary / exec_bridge fallback 化
- Kaikun04 direct EXEC を primary とする構成を実地確認
- 検証:
 - router_tasks id=565 -> exec_bridge_status='direct'
 - exec_child_task_id=566
 - child task 566 は ops_exec done
 - self_improvement_log latest は kind='exec_direct' status='done'
- `kaikun04_exec_bridge_v1` は `coalesce(exec_child_task_id,0)=0` 条件を追加
- これにより direct child 済み task は bridge が再取得しない
- exec_bridge は fallback として待機

## 2026-04-02 Kaikun mode / exec policy
- `task_router_v1` は `target='kaikun04'` 固定・mode未付与の入口へ簡素化済み
- `kaikun04_router_worker_v1` は `decide_mode()` で mode を内部判定
- `kaikun04_router_worker_v1` は `decide_exec_policy()` で EXEC を `auto / confirm / deny` 制御
- `router_tasks` に `decided_mode` / `exec_policy` を保存する構成へ更新

## 2026-04-02 cleanup after Kaikun decision-layer rollout
- 旧 failed router_tasks を整理
- routed のまま残っていた new inbox_commands を skipped 処理
- 直近本線は `kaikun04 -> direct child ops_exec -> self_improvement_log` で通過確認済み
- 現在は decision metadata (`decided_mode` / `exec_policy`) 保存よりも mainline 安定を優先

## 2026-04-02 exec provider abstraction
- `telegram_ops_executor_v1.py` に `run_local()` / `run_openclaude()` / `run_script()` 分岐を導入
- `EXEC_PROVIDER=local|openclaude` で実行先を切替可能な構造へ変更
- 現時点では `openclaude` は simulation 実装で疎通確認までを対象
- 本線は引き続き local 実行を維持

## 2026-04-02 n8n recovery priority
- npm 版 n8n は `isolated-vm` / `distutils` 依存で失敗
- Docker Desktop は未導入だったため、Colima + Docker へ切替
- n8n は Docker コンテナで起動する方針へ変更
- 事業化より先に基盤強化を優先

## 2026-04-03 n8n to OpenClaw mainline established
- n8n webhook -> HTTP Request -> api_server.py -> inbox_commands 挿入成功
- n8n source の inbox_commands が task_router を通り kaikun04 task 化されることを確認
- kaikun04 done / ok を確認
- ops_exec child task done / ok を確認
- telegram_ops_executor_v1 は DB_PATH 固定 launch script で fresh log clean
- 現在の本線は n8n -> API -> inbox_commands -> task_router -> kaikun04 -> ops_exec

## 2026-04-03 mainline stabilization finalized
- n8n -> api_server -> inbox_commands -> task_router -> kaikun04 -> ops_exec を継続実証
- telegram_ops_executor_v1 fresh log は `done=0` のみで clean
- api_server は LaunchAgent 管理へ一本化
- n8n production webhook からの投入を正式ルートとして固定

## 2026-04-03 Telegram entrance integration preparation
- 入口方針は Telegram -> n8n -> api_server -> inbox_commands を primary とする
- private_reply_to_inbox_v1 は既存 private ingest の fallback として維持
- api_server.py は source 指定を受けられる入口APIへ拡張
- task_router_v1 は空 mode の `[]` タグを出さない形へ整理

## 2026-04-03 Telegram primary entrance established
- スマホから Tailscale 経由で n8n にアクセス可能
- n8n は `~/.n8n` bind mount で永続化
- n8n HTTP Request は `source=telegram_n8n` + `text` 形式へ統一
- Telegram primary entrance は `Telegram -> n8n -> api_server -> inbox_commands` として実地確認済み
- `telegram_primary` / `telegram_n8n` source で kaikun04 / ops_exec 完走を確認

## 2026-04-03 Telegram route role split
- primary route は `Telegram -> n8n -> api_server -> inbox_commands -> task_router -> kaikun04`
- fallback route は `private_reply_to_inbox_v1` と `manual insert`
- `secretary_llm_v1` は current primary ではなく legacy / fallback 側の構成要素
- current primary の reply mainline は task_router / kaikun04 / router_reply_finisher / ops_exec で成立

## 2026-04-03 primary route burn-in confirmation
- `telegram_n8n` source で primary route の burn-in を追加確認
- inbox_commands id=555 は done / sent
- router_tasks id=618 は kaikun04 done / ok
- router_tasks id=619 は ops_exec done / ok
- secretary_llm_v1 は current primary route には含まれず、legacy / fallback として扱う

## 2026-04-03 fallback reduction candidate identified
- secretary_llm_v1 は停止対象ではなく observe / fallback candidate として整理
- private_reply_to_inbox_v1 / ingest_private_replies_kaikun04 は emergency fallback として維持
- Telegram -> n8n primary は継続 burn-in 対象

## 2026-04-03 fallback status clarified
- global launchctl DB env 汚染を除去後、private_reply_to_inbox_v1 は error なく待機することを確認
- private_reply_to_inbox_v1 は usable fallback として維持可能
- ingest_private_replies_kaikun04 LaunchAgent は bots/ingest_private_replies_v1.py を実行しており、名称と実体にズレがある
- ingest_private_replies_kaikun04 は legacy-named fallback として扱う

## 2026-04-03 operational classification fixed
- required primary:
  api_server / task_router_v1 / kaikun04_router_worker_v1 / telegram_ops_executor_v1 / router_reply_finisher_v1
- usable fallback:
  private_reply_to_inbox_v1 / manual insert
- observe or legacy fallback:
  ingest_private_replies_kaikun04 / secretary_llm_v1
- 現時点では observe 化の明文化を優先し、命名整理は後段とする

## 2026-04-03 telegram route runtime check added
- `scripts/check_telegram_route_runtime.sh` を追加し、primary / fallback / recent source を 1コマンドで確認可能にした
- 日常運用では分類固定だけでなく runtime snapshot の確認を優先する

## 2026-04-03 legacy fallback naming policy fixed
- `jp.openclaw.ingest_private_replies_kaikun04` は 名 称 上 は kaikun04 ingest だ が 、 runtime 実 体 は `bots/ingest_private_replies_v1.py`
- よ っ て 現 時 点 で は clean primary 候 補 で は な く legacy-named fallback と し て 扱 う
- rename は primary burn-in を さ ら に 積 ん だ 後 段 へ 回 す

## EXECライン安定化完了（2026-04-05）

### 修正内容
- telegram_ops_executor_v1
  - DB接続リトライ導入
  - stale started 回収（10分）
- ops/telegram_exec/deploy_safe.sh
  - executor自己再起動ループ解消
- scripts/run_kaikun04_exec_bridge_v1.sh
  - DB_PATH明示
- kaikun04_router_worker_v1
  - malformed EXEC除去（force_clean_exec）
  - contextベースのEXEC選択強化

### 状態
- EXEC成功率: 97.7%（86/88）
- failed: 0
- skipped: 2（過去分のみ）
- started/new滞留: 0

### 結果
- EXECラインは自動回復・自己修復構造へ到達
- 手動介入なしで安定稼働
- EXEC HEALTH は ceo_hub_events へ送信可能

### 次フェーズ
- EXECレポートの定期送信
- EXEC精度の継続改善
- 収益ライン接続

## 2026-04-05 TECH ADOPTION SYSTEM

### 方針
- 無料優先
- ローカル優先
- API依存は最小化
- Xは発見専用（採用判断は別）
- GitHub / 公式 / Reddit を優先ソースとする

### フロー
1. scout（収集）
2. judge（採用判定）
3. reporter（通知）
4. adopter（導入）

### 採用基準
- free = 必須
- local = 強優先
- OpenClaw能力向上に直結
- 実装コスト低

### status
- adopt
- hold
- reject

### 次段
- 案件処理テンプレ
- 収益ライン接続

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

