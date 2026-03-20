# OpenClaw Runtime Classification

## source of truth
- DB: /Users/doyopc/AI/openclaw-factory/data/openclaw.db
- docs より実DB / 実process / watcher event を優先する

## watcher policy
### required
- jp.openclaw.ops_brain_agent_v1

### observe
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
- jp.openclaw.ingest_private_replies_kaikun02
- jp.openclaw.ingest_private_replies_kaikun04

## mainline data signals
- dev_proposals: 3265
- merged: 2624
- open_pr: 0
- proposal_state: 171
- ceo_hub_events: 35379
- ops_watcher_events: 3665

## schema notes
### ceo_hub_events
- id
- event_type
- title
- body
- proposal_id
- pr_url
- created_at
- sent_at

### ops_watcher_events
- id
- kind
- body
- created_at

## legacy or archive candidate
- ceo_terminal_* 系
- ceo_final_* 系
- selector / normalizer / bridge 派生の旧系列
- cleanup 系
- 127 / 78 で停止中の旧 bot 群

## judgment rule
- observe stopped は障害扱いしない
- required の health failure のみ一次障害扱い
- docs の古い参照より runtime 実態を優先


## ops note
- ops_brain_v1 is current production entrypoint in openclaw-factory
- run_ops_brain_agent.sh / run_ops_brain_watcher.sh both call factory bots/ops_brain_v1.py
- daemon-side ops_brain_v4 is experimental only

- kaikun04 legacy router worker/cleanup path is retired; current active private reply path is ingest_private_replies_kaikun04

- kaikun02 private reply worker path is retired; current active private reply path is ingest_private_replies_kaikun02

## retired missing-target plists
- jp.openclaw.kaikun02_coo_controller_v1 plist retired: missing target script
- jp.openclaw.kaikun02_executor_bridge_v2 plist retired: missing target script
- jp.openclaw.kaikun02_health_gate_v1 plist retired: missing target script
- jp.openclaw.kaikun02_router_cleanup_v1 plist retired: missing target script
- jp.openclaw.kaikun02_router_worker_v1 plist retired: missing target script
- jp.openclaw.kaikun04_router_cleanup_v1 plist retired: missing target script
- jp.openclaw.kaikun04_router_worker_v1 plist retired: missing target script
- task_router_v1 is active runtime router path and must not be archived blindly
- router_reply_finisher_v1 is active runtime finisher path and must not be archived blindly
- router_stall_watchdog_v1 is active runtime watchdog path and must not be archived blindly
