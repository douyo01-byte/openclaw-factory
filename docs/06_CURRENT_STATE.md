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
- 実運用の判断は docs より実DB / 実process / watcher event を優先する
- 本番DBは /Users/doyopc/AI/openclaw-factory/data/openclaw.db
- /Users/doyopc/AI/openclaw-factory-daemon/data/openclaw_real.db は現時点では本番ではない

## watcher summary
### required
- jp.openclaw.ops_brain_agent_v1

### observe stopped
- jp.openclaw.dev_pr_automerge_v1
- jp.openclaw.db_integrity_watchdog_v1
- jp.openclaw.kaikun02_coo_controller_v1

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

### router
- task_router_v1
- kaikun02_router_worker_v1
- kaikun04_router_worker_v1
- router_reply_finisher_v1
- kaikun02_router_cleanup_v1
- kaikun04_router_cleanup_v1
- router_stall_watchdog_v1

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


## ACTIVE本 流
- private reply:
  - ingest_private_replies_kaikun04
  - private_reply_to_inbox_v1
  - secretary_llm_v1
- router:
  - task_router_v1
  - kaikun02_router_worker_v1
  - kaikun04_router_worker_v1
  - router_reply_finisher_v1
  - kaikun02_router_cleanup_v1
  - kaikun04_router_cleanup_v1
  - router_stall_watchdog_v1
- watcher required:
  - jp.openclaw.ops_brain_agent_v1
  - jp.openclaw.private_reply_to_inbox_v1
  - jp.openclaw.secretary_llm_v1
- watcher observe:
  - jp.openclaw.dev_pr_automerge_v1
  - jp.openclaw.db_integrity_watchdog_v1
  - jp.openclaw.kaikun02_coo_controller_v1
  - jp.openclaw.dev_pr_watcher_v1
  - jp.openclaw.ingest_private_replies_kaikun04


## THINK timeout fallback
- THINK task が timeout し reply_text 空 の 場合
- router_timeout_fallback_v1 が fallback を 生成
- result_text に fallback_sent を 記録
- task 自体 の status は timeout の まま保持
