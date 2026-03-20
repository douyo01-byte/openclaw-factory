# DAILY OPERATION

## first checks
1. ~/AI/openclaw-factory-docs/check_state.sh
2. openclaw.db counts
3. ceo_hub_events latest rows
4. ops_watcher_events latest rows

## judgment
- docs より runtime を優先
- observe stopped は一次障害扱いしない
- required health failure のみ優先対応

## current mainline
- ops_brain_agent_v1
- ops_brain_watcher_v1
- dev_pr_watcher_v1
- proposal_cluster_v1
- pattern_extractor_v1
- supply_bias_updater_v1
- ceo_priority_scorer_v1
- ingest_private_replies_kaikun02
- ingest_private_replies_kaikun04
