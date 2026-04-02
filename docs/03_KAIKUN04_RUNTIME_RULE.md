
## EXEC統合方針（2026-04）

- Kaikun04は返信時にEXECを生成するだけでなく
  child task（ops_exec）を直接生成する責務を持つ

- exec_bridge_v1は暫定的に維持するが
  将来的には削除する

- 条件：
  - reply_text に [EXEC] がある場合
  - script=xxx が抽出できる場合

- 処理：
  1. router_tasks に child task を insert
  2. parent に child_task_id を紐付け
  3. self_improvement_log に記録

