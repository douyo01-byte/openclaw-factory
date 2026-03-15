
## Kaikun02 固定運用ルール
- live runtime は docs より DB と audit を優先
- 実働安全系:
  - open_pr_guard_v1
  - dev_pr_watcher_v1
  - dev_pr_creator_v1
  - proposal_promoter_v1
  - spec_refiner_v2
  - spec_decomposer_v1
  - proposal_throttle_engine_v1
  - learning_result_writer_v1
- 停止維持:
  - innovation_engine_v1
  - strategy_engine_v1
  - proposal_builder_loop_v1
  - reasoning_engine_v1
- producer再開は backlog投入のみ許可
- approved / execute_now / open PR を直接増やす変更は禁止

## Kaikun02 参照優先順
1. docs/06_CURRENT_STATE.md
2. docs/10_RUNTIME_AUDIT_STATUS.md
3. docs/99_CONNECTED_RUNTIME_PATCH.md
4. ../openclaw-factory-daemon/reports/audit_20260315/final_runtime_status.md
5. ../openclaw-factory-daemon/reports/audit_20260315/kaikun02_runtime_memo.md
6. ../openclaw-factory-daemon/reports/audit_20260315/connected_asset_inventory.md
7. ../openclaw-factory-daemon/reports/audit_20260315/docs_live_gap.md
8. ../openclaw-factory-daemon/reports/audit_20260315/producer_enable_order.md
