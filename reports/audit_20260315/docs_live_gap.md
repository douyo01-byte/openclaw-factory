# DOCS vs LIVE GAP

## LIVE
- unique_open_prs: 15
- open_pr_by_source:
  - mothership: 6
  - innovation_engine: 4
  - cto: 3
  - strategy_engine: 2

## pipeline_top20
- execute_now | merged | decomposed | merged | 1301
- execute_now | merged | refined | merged | 816
- execute_now | merged |  | merged | 376
- execute_now | closed | decomposed | closed | 88
- execute_now | blocked_target_policy | refined |  | 11
- execute_now | open | decomposed | open | 8
- backlog |  | raw |  | 6
- execute_now | open | refined | open | 4
- blocked_target_policy | blocked_target_policy |  |  | 2
- execute_now | closed |  | closed | 2
- execute_now | open | raw | open | 2
-  |  |  |  | 1
-  | closed |  |  | 1
- execute_now | open |  | open | 1

## required_doc_updates
- docs/06_CURRENT_STATE.md は旧状態値を含むため live DB 基準へ更新要
- docs/08_HANDOVER.md は旧 launchagent/runtime 記述を含むため audit_20260315 基準へ更新要
- docs/99_CONNECTED_RUNTIME_PATCH.md は接続台帳として有効
