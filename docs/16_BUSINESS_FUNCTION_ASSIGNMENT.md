# BUSINESS FUNCTION ASSIGNMENT

## purpose
scout_market_v2 / chat_research_v1 の 関 数 を 既 存 mainline 側 へ
ど こ に 吸 収 す る か を 関 数 単 位 で 固 定 す る 。

## fixed rule
- 新 規 bot は 作 ら な い
- 単 体 LaunchAgent は 復 活 し な い
- 関 数 抽 出 → 既 存 file 統 合 の 順 で 行 う
- ま ず utility 化 対 象 を 固 定 し 、 そ の 後 に 実 装 す る

## scout_market_v2 assignment
### to bots/team/sakura_scout.py
- load_sources
- fetch_rss
- key_for
- is_seen
- mark_seen
- save_item

### to bots/team/miho_finder.py
- save_contacts

### hold / redesign later
- llm_score
- format_tg
- format_meeting
- main

## chat_research_v1 assignment
### to bots/meeting_from_db_v1.py
- normalize_base
- fetch
- extract_signals
- summarize
- enqueue_contact
- upsert_role_brief

### to bots/chat_router_v1.py
- get_item
- set_ctx_last_item 相 当 の 文 脈 更新 方 針
- chat_jobs 起 点 の 呼 び 出 し 境 界 整 理

### hold / redesign later
- build_reply
- main

## explicit non-target
- bots/ops_brain_v1.py
- scripts/run_ops_brain_agent.sh
- scripts/run_ops_brain_watcher.sh

## implementation order
1. sakura_scout.py に scout utility を 吸 収
2. miho_finder.py に contact save 方 針 を 吸 収
3. meeting_from_db_v1.py に research utility を 吸 収
4. chat_router_v1.py に chat_jobs 境 界 を 固 定
5. そ の 後 に mainline 統 合 実 装 開 始
