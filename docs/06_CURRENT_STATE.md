# OpenClaw Current State

- generated_at: 2026-03-22
- canonical_db: /Users/doyopc/AI/openclaw-factory/data/openclaw.db

## 現在地
- AI企業レベル: Lv7〜Lv8
- maturity: 自己進化本線へ再編中
- burn-in: 前段整理中

## live counters
- dev_proposals: 3261
- merged: 2624
- open_pr: 0
- proposal_state: 171
- ceo_hub_events: 35379
- ops_watcher_events: 3174

## source of truth
- 実運用の判断は docs より 実DB / 実process / watcher event を優先する
- 本番DBは /Users/doyopc/AI/openclaw-factory/data/openclaw.db
- /Users/doyopc/AI/openclaw-factory-daemon/data/openclaw_real.db は現時点では本番ではない

## watcher summary
### required
- jp.openclaw.ops_brain_agent_v1
- jp.openclaw.private_reply_to_inbox_v1
- jp.openclaw.secretary_llm_v1

### observe
- jp.openclaw.dev_pr_automerge_v1
- jp.openclaw.db_integrity_watchdog_v1
- jp.openclaw.kaikun02_coo_controller_v1
- jp.openclaw.dev_pr_watcher_v1
- jp.openclaw.ingest_private_replies_kaikun04

## mainline active
- jp.openclaw.ops_brain_agent_v1
- jp.openclaw.dev_pr_watcher_v1
- jp.openclaw.proposal_cluster_v1
- jp.openclaw.pattern_extractor_v1
- jp.openclaw.supply_bias_updater_v1
- jp.openclaw.ceo_priority_scorer_v1

## note
- ceo_hub_events の主要本文列は summary ではなく title / body
- ops_watcher_events の主要列は kind / body
- open_pr は 0 で健全
- watcher は required 対象に対して正常

## ACTIVE本流
### dev pipeline
- dev_proposals
- spec_refiner_v2
- dev_executor_v1
- dev_pr_watcher_v1
- dev_pr_automerge_v1

### private reply
- ingest_private_replies_kaikun04
- private_reply_to_inbox_v1
- secretary_llm_v1
- inbox_commands.secretary_done

### watcher
- required:
  - jp.openclaw.ops_brain_agent_v1
  - jp.openclaw.private_reply_to_inbox_v1
  - jp.openclaw.secretary_llm_v1
- observe:
  - jp.openclaw.dev_pr_automerge_v1
  - jp.openclaw.db_integrity_watchdog_v1
  - jp.openclaw.kaikun02_coo_controller_v1
  - jp.openclaw.dev_pr_watcher_v1
  - jp.openclaw.ingest_private_replies_kaikun04

## private_reply_to_inbox_v1 bridge stability
- run_private_reply_to_inbox_v1.sh は absolute path 固定
- DB_PATH / OCLAW_DB_PATH / FACTORY_DB_PATH を同時 export
- launchd 実行での unable to open database file を解消
- private tg log -> inbox_commands -> secretary_done を再確認済み

## Private Reply Single Source

    Telegram(private)
    -> tg_private_chat_log
    -> private_reply_to_inbox_v1
    -> inbox_commands
    -> secretary_llm_v1
    -> secretary_done

Legacy router runtimes were archived into archive/router_legacy_20260322 and are not part of the active private reply path.

## Private Reply Mainline
- Telegram(private)
- tg_private_chat_log
- ingest_private_replies_kaikun04
- private_reply_to_inbox_v1
- inbox_commands
- secretary_llm_v1
- secretary_done

## Router Structure
- Kaikun02 = FAST
- Kaikun04 = THINK

## Entry Gate / Input Guard
- blank / 1文字 / URL単体 は除外
- duplicate 抑止
- short = fast
- long / [THINK] / 分析要求 = think

## Watcher Definition
### required
- jp.openclaw.private_reply_to_inbox_v1
- jp.openclaw.secretary_llm_v1

### observe
- jp.openclaw.ingest_private_replies_kaikun04

