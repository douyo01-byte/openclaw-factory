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
- jp.openclaw.ceo_priority_scorer_v1

## mainline data signals
- dev_proposals: 3261
- merged: 2624
- open_pr: 0
- proposal_state: 171
- ceo_hub_events: 35379
- ops_watcher_events: 3174

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

- kaikun04_router_worker_v1 / kaikun04_router_cleanup_v1 are disabled as non-mainline legacy router artifacts

- kaikun02_router_worker_v1 is disabled as non-mainline legacy router artifact

## retired missing-target plists
- jp.openclaw.kaikun02_coo_controller_v1 plist retired: missing target script
- jp.openclaw.kaikun02_executor_bridge_v2 plist retired: missing target script
- jp.openclaw.kaikun02_health_gate_v1 plist retired: missing target script
- jp.openclaw.kaikun02_router_cleanup_v1 plist retired: missing target script
- jp.openclaw.kaikun02_router_worker_v1 plist retired: missing target script
- jp.openclaw.kaikun04_router_cleanup_v1 plist retired: missing target script
- jp.openclaw.kaikun04_router_worker_v1 plist retired: missing target script

## ceo legacy classification
## dead_no_runtime
- none

## plist_only
- jp.openclaw.ceo_decision_layer_v1 | state=stopped | plist=true | code_ref=0 | doc_ref=2
- jp.openclaw.ceo_executor_guarded_promoter_v1 | state=running | plist=true | code_ref=0 | doc_ref=2
- jp.openclaw.ceo_final_executor_guarded_promoter_v1 | state=running | plist=true | code_ref=0 | doc_ref=3
- jp.openclaw.ceo_growth_reviewer_v1 | state=running | plist=true | code_ref=0 | doc_ref=2
- jp.openclaw.ceo_guarded_executor_priority_fixer_v1 | state=running | plist=true | code_ref=0 | doc_ref=2
- jp.openclaw.ceo_guarded_mainline_priority_fixer_v1 | state=running | plist=true | code_ref=0 | doc_ref=2
- jp.openclaw.ceo_guarded_mainline_promoter_v1 | state=running | plist=true | code_ref=0 | doc_ref=2
- jp.openclaw.ceo_hub_sender_v1 | state=running | plist=true | code_ref=0 | doc_ref=2
- jp.openclaw.ceo_priority_fixer_v1 | state=running | plist=true | code_ref=0 | doc_ref=2
- jp.openclaw.ceo_priority_scorer_v1 | state=running | plist=true | code_ref=0 | doc_ref=4
- jp.openclaw.ceo_proposal_reviewer_v1 | state=running | plist=true | code_ref=0 | doc_ref=2

## legacy_doc_only
- none

## needs_manual_review
- none

## retired missing-target ceo plists
- jp.openclaw.ceo_terminal_executor_guarded_normalizer_v1 plist retired: missing target script
- jp.openclaw.ceo_terminal_executor_guarded_selector_v1 plist retired: missing target script
- jp.openclaw.ceo_terminal_final_executor_bridge_v1 plist retired: missing target script
- jp.openclaw.ceo_terminal_final_executor_normalizer_v1 plist retired: missing target script
- jp.openclaw.ceo_terminal_final_executor_selector_v1 plist retired: missing target script
- jp.openclaw.ceo_terminal_guard_normalizer_v1 plist retired: missing target script
- jp.openclaw.ceo_terminal_guard_selector_v1 plist retired: missing target script
