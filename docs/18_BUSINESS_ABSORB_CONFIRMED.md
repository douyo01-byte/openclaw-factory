# BUSINESS ABSORB CONFIRMED

## confirmed absorb map
### bots/team/sakura_scout.py
- load_sources
- fetch_rss
- key_for
- is_seen
- mark_seen
- save_item

### bots/team/miho_finder.py
- save_contacts

### bots/meeting_from_db_v1.py
- normalize_base
- fetch
- extract_signals
- summarize
- enqueue_contact
- upsert_role_brief

### bots/chat_router_v1.py
- get_item
- ctx:last_item 更新方針
- chat_jobs enqueue 境界

## confirmed non-absorb
- llm_score
- format_tg
- format_meeting
- build_reply
- standalone main loops

## fixed rule
- 単体 bot 復活なし
- 新規 LaunchAgent なし
- utility 抽出 → 既存 file 吸収 → その後に mainline 統合
