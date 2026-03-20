# BUSINESS FUNCTION EXTRACTION PLAN

## scout_market_v2
### function inventory
- _load_persona_from_env
- save_item
- db
- key_for
- is_seen
- mark_seen
- save_contacts
- load_sources
- fetch_rss
- llm_score
- format_tg
- format_meeting
- main

### reusable priority
- load_sources
- fetch_rss
- key_for
- is_seen
- mark_seen
- save_item
- save_contacts

### non-direct reuse
- llm_score
- format_tg
- format_meeting
- main

## chat_research_v1
### function inventory
- connect_db
- now_str
- fetch
- normalize_base
- extract_signals
- summarize
- get_item
- set_ctx_last_item
- enqueue_contact
- upsert_role_brief
- build_reply
- main

### reusable priority
- fetch
- normalize_base
- extract_signals
- summarize
- get_item
- enqueue_contact
- upsert_role_brief

### non-direct reuse
- build_reply
- main

## integration rule
- 単体 bot として復活しない
- 関数単位で mainline に吸収する
- items / contacts / chat_jobs / role_briefs を触る処理だけを分離対象にする
- Telegram送信や常駐loopは統合先で再設計する

## next implementation order
1. scout_market_v2 の reusable priority を utility 化
2. chat_research_v1 の reusable priority を utility 化
3. DB更新関数を mainline 呼び出し前提に分離
4. mainline へ最小差分で統合
