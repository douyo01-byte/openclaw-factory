# OpenClaw Architecture

このドキュメントは OpenClaw の全体構造を俯瞰するための設計図です。
会話ログではなく、実ファイル / 実DB / 実ログ / 実プロセスを優先して更新してください。

---

# 全体像

OpenClaw は大きく以下の層で構成されます。

1. docs 層
2. 実行プロセス層
3. bot / script 層
4. DB 層
5. 外部連携層

---

# 1. docs 層

基準となる正本は以下です。

- docs/01_SYSTEM_PROMPT.md
- docs/06_CURRENT_STATE.md
- docs/08_HANDOVER.md

補助 docs

- docs/00_INDEX.md
- docs/11_OPERATIONS.md
- docs/17_EFFICIENCY_RULES.md
- docs/20_DAILY_OPERATION.md
- docs/README.md
- docs/02_MASTER_PLAN.md

役割

- 母艦の判断基準
- 次チャットへの引き継ぎ
- 運用ルール固定
- 実測値の集約
- 全体構造の把握

---

# 2. 実行プロセス層

現在の主要常駐プロセスの中核は以下です。

- supervisor
- dev_command_executor
- dev_pr_watcher
- tg_poll_loop
- self_healing

役割

supervisor
- 全体監視
- 主要 loop の維持

dev_command_executor
- 開発指示の実行
- コード変更
- PR 作成系処理

dev_pr_watcher
- PR 状態監視
- merged 反映
- proposal_state 更新

tg_poll_loop
- Telegram 受信
- private / group 系の取込
- 周辺通知系の周期実行ハブ

self_healing
- 停止検知
- 再起動補助
- 崩れた運用の自動回復

---

# 3. bot / script 層

主要 bot / script は以下の役割分担で動作します。

開発実行系
- dev_command_executor
- dev_pr_watcher

Telegram 取込系
- tg_poll_loop
- ingest 系 script / bot

安定化系
- self_healing
- supervisor

docs 保守系
- scripts/fix_docs_spacing.py

役割原則

- bot は単機能寄り
- 常駐制御は loop / LaunchAgent 側
- 状態の正本は DB と実プロセス
- docs は現状を要約して追従

---

# 4. DB 層

基準 DB

- sqlite3 data/openclaw.db

現在の主要テーブル例

- dev_proposals
- proposal_state
- proposal_conversation
- inbox_commands
- decisions
- ceo_hub_events

代表役割

dev_proposals
- 開発案件の母表

proposal_state
- 案件進行状態
- refined / merged / executed / pr_created などの状態管理

proposal_conversation
- 案件に紐づく会話ログ

inbox_commands
- 受信コマンド管理

decisions
- 判断記録

ceo_hub_events
- merged
- learning_result
- pr_created
などの経営共有イベント記録

---

# 5. 外部連携層

主な接続先

- Telegram
- GitHub
- LaunchAgent
- ローカルログ
- SQLite DB

役割

Telegram
- 指示入力
- 通知
- 会話窓口

GitHub
- PR 作成
- merge 状態取得
- 開発成果反映

LaunchAgent
- macOS 常駐運用
- 自動起動
- 監視対象の維持

ログ
- 実運用確認
- 障害切り分け

---

# データの優先順位

OpenClaw は以下の優先順位で判断します。

1. 実ファイル
2. 実DB
3. 実ログ
4. 実プロセス
5. docs
6. 会話ログ

---

# 更新原則

architecture docs 更新時は以下を守ります。

- 推測で書かない
- 実在する bot / script / table のみ反映
- LaunchAgent の running 状態は実測で更新
- DB 件数は sqlite3 実測値で更新
- スマホ更新後は spacing 修正を行う

---

# 現在の把握済み状態

現時点で確認済みの実状態

- supervisor / dev_command_executor / dev_pr_watcher / tg_poll_loop / self_healing は running
- dev_proposals は 808
- proposal_state は refined=11 / merged=2 / executed=1 / pr_created=1
- ceo_hub_events は merged=50 / learning_result=4 / pr_created=3

この章は実測で定期更新すること。
