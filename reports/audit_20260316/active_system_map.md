# ACTIVE SYSTEM MAP 2026-03-16

## core proposal pipeline
proposal_promoter_v1
→ spec_refiner_v2
→ spec_decomposer_v1
→ dev_pr_creator_v1
→ dev_pr_watcher_v1
→ auto_merge_cleaner_v1

## guard / health
open_pr_guard_v1
kaikun02_health_gate_v1

## operating control
kaikun02_coo_controller_v1
kaikun02_executor_bridge_v2

## current intent
- promoter converts backlog/approved into open + execute_now + raw
- refiner converts open + execute_now + raw into refined spec
- decomposer converts refined into decomposed + ready
- pr_creator creates/reuses PR and moves row to pr_created/open
- watcher syncs GitHub PR state into DB
- auto_merge_cleaner drains clean open PR backlog
- Kaikun02 reads health and decides next executable action set

## burn-in pass conditions
- open PR count = 0 at idle
- no legacy DB reference in active LaunchAgents
- no blank source_ai
- watcher loop quiet
- no stuck open/approved/backlog rows except intentional throttled rows
