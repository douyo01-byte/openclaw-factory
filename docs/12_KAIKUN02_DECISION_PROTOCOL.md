# KAIKUN02 DECISION PROTOCOL

## 優先参照
1. docs/06_CURRENT_STATE.md
2. docs/10_RUNTIME_AUDIT_STATUS.md
3. docs/99_CONNECTED_RUNTIME_PATCH.md
4. ../openclaw-factory-daemon/reports/audit_20260315/final_runtime_status.md
5. ../openclaw-factory-daemon/reports/audit_20260315/final_task_completion.md
6. ../openclaw-factory-daemon/reports/audit_20260315/kaikun02_runtime_memo.md
7. ../openclaw-factory-daemon/reports/audit_20260315/kaikun02_health_gate.md
8. ../openclaw-factory-daemon/reports/audit_20260315/docs_live_gap.md

## 判断原則
- docsより live DB / audit を優先
- gate_ok=no のとき keep_stopped は起動禁止
- approved / execute_now / open PR を増やす producer 再開は禁止
- producer は backlog 投入モードのみ許可
- blank source の open 行は即修正対象

## safe_prod_now
- open_pr_guard_v1
- dev_pr_watcher_v1
- dev_pr_creator_v1
- proposal_promoter_v1
- spec_refiner_v2
- spec_decomposer_v1
- proposal_throttle_engine_v1
- learning_result_writer_v1

## keep_stopped
- innovation_engine_v1
- strategy_engine_v1
- proposal_builder_loop_v1
- reasoning_engine_v1

## 出力フォーマット
### judgment
- gate_ok: yes/no
- action: start_allowed / keep_stopped_only
- reason: 1行

### active_now
- safe_prod_now の実稼働一覧

### blocked_now
- keep_stopped の停止維持一覧

### next_touch
- 次に触るべき bot / file / table を最大3件

### db_watch
- unique_open_prs
- duplicate_open_pr_url
- blank_source_open_rows
