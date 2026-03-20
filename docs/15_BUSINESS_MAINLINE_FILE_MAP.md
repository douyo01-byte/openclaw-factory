# BUSINESS MAINLINE FILE MAP

## purpose
business 再 設 計 時 に 、 scout_market_v2 / chat_research_v1 の 吸 収 先 を 既 存 ファイル 単 位 で 固 定 す る 。

## fixed rule
- 新 規 bot は 作 ら な い
- 単 体 LaunchAgent は 復 活 し な い
- 関 数 抽 出 → 既 存 ファイル へ 統 合 の 順 で 行 う
- ops_brain に は business ロ ジ ッ ク を 入 れ な い

## file map

### 1. chat job intake
- target file: bots/chat_router_v1.py
- role:
  - item 特 定
  - chat_jobs enqueue
  - role 振 り 分 け
- absorb candidates:
  - get_item 相 当 の 再 利 用
  - chat_research 系 の job 起 点 整 理

### 2. research execution
- target file: bots/meeting_from_db_v1.py
- role:
  - items / role_briefs / contacts を 使 う DBベース処 理
  - business 会 話 出 力 側 の 中 核 候 補
- absorb candidates:
  - normalize_base
  - fetch
  - extract_signals
  - summarize
  - enqueue_contact
  - upsert_role_brief

### 3. item enrichment / official contact side
- target file: bots/team/miho_finder.py
- role:
  - items へ official_url / contact 補 強
- absorb candidates:
  - save_contacts の 役 割 分 離
  - contact 抽 出 後 の 保存方針 整 理

### 4. feed / source ingestion seed
- target file: bots/team/sakura_scout.py
- role:
  - source 由 来 の 候 補 収 集 ロ ジ ッ ク
- absorb candidates:
  - load_sources
  - fetch_rss
  - key_for
  - is_seen
  - mark_seen
  - save_item

## explicit non-target
- bots/ops_brain_v1.py
- scripts/run_ops_brain_agent.sh
- scripts/run_ops_brain_watcher.sh
- dev_pr_watcher_v1 系
- proposal_cluster_v1 系
- pattern_extractor_v1 系
- supply_bias_updater_v1 系

## next implementation order
1. chat_router_v1.py へ job intake 境界 を 固 定
2. meeting_from_db_v1.py へ research utility 境界 を 固 定
3. miho_finder.py / sakura_scout.py へ item/contact utility を 分 配
4. そ の 後 に mainline 統 合 実 装 開 始
