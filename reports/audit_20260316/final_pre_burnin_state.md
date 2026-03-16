# FINAL PRE-BURNIN STATE 2026-03-16

## summary
- merged blank spec_stage normalized to decomposed
- active core pipeline runner paths standardized
- legacy openclaw_real.db launchagents archived out of active tree
- runtime inventory regenerated into ACTIVE / RESERVE / LEGACY buckets
- active system map documented for Kaikun02
- final audits saved under reports/audit_20260316

## expected interpretation
- database of record is /Users/doyopc/AI/openclaw-factory/data/openclaw.db
- active core path is:
  proposal_promoter_v1
  -> spec_refiner_v2
  -> spec_decomposer_v1
  -> dev_pr_creator_v1
  -> dev_pr_watcher_v1
  -> auto_merge_cleaner_v1
- control path is:
  kaikun02_health_gate_v1
  -> kaikun02_coo_controller_v1
  -> kaikun02_executor_bridge_v2
- guard path is:
  open_pr_guard_v1

## burn-in gate
- open PR count must stay 0 at idle
- blank source_ai must stay 0
- legacy DB refs in active tree must be 0
- watcher must stay quiet
- no unexpected open/backlog/approved rows
