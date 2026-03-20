# OpenClaw Current State

- generated_at: 2026-03-19
- canonical_db: /Users/doyopc/AI/openclaw-factory/data/openclaw.db

## 現在地
- AI企業レベル: Lv7〜Lv8
- maturity: 自己進化本線へ再編中
- burn-in: 前段整理中

## live counters
- dev_proposals: 3236
- merged: 2624
- open_pr: 0
- proposal_state: 171
- ceo_hub_events: 35379
- ops_watcher_events: 1451

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
- jp.openclaw.brain_supply_v1
- jp.openclaw.proposal_cluster_v1
- jp.openclaw.pattern_extractor_v1
- jp.openclaw.supply_bias_updater_v1
- jp.openclaw.ceo_priority_scorer_v1

## note
- ceo_hub_events の主要本文列は summary ではなく title / body
- ops_watcher_events の主要列は kind / body
- open_pr は 0 で健全
- watcher は required 対象に対して正常
