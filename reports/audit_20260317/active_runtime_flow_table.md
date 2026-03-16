# ACTIVE Runtime Flow Table (2026-03-17)

| bot | input | process | output | next |
|---|---|---|---|---|
| proposal_promoter_v1 | dev_proposals backlog/new | 昇格・起票整理 | dev_proposals promoted | spec_refiner_v2 |
| spec_refiner_v2 | dev_proposals promoted | 仕様具体化 | proposal_conversation / proposal_state / refined proposal | spec_decomposer_v1 |
| spec_decomposer_v1 | refined proposal | 実装単位へ分解 | executor-ready proposal | dev_pr_creator_v1 |
| dev_pr_creator_v1 | executor-ready proposal | ブランチ/変更/PR作成 | pr_url / pr_status=open | dev_pr_watcher_v1 |
| dev_pr_watcher_v1 | open PR | PR状態追跡 | merged state / ceo_hub_events | auto_merge_cleaner_v1 |
| auto_merge_cleaner_v1 | merged PR | 後始末・状態同期 | dev_proposals merged整合 | learning_brain_v1 |
| learning_brain_v1 | merged proposal / ceo_hub_events | 学習抽出 | decision_patterns / learning feedback | innovation_llm_engine_v1 |
| innovation_llm_engine_v1 | learning結果 / supply_bias | 次改善案生成 | new dev_proposals | proposal_promoter_v1 |
| task_router_v1 | inbox_commands | bot振り分け | router_tasks | kaikun02_router_worker_v1 / kaikun04_router_worker_v1 |
| kaikun02_router_worker_v1 | router_tasks(target=kaikun02) | quick reply or task relay | done/started router_tasks | private reply / router_reply_finisher |
| secretary_llm_v1 | inbox_commands | dashboard/route/context reply | secretary_done | user / CEO chat |
| kaikun02_health_gate_v1 | dev_proposals / runtime state | 健全性判定 | health gate result | kaikun02_coo_controller_v1 |
| kaikun02_coo_controller_v1 | health gate result | COO判断 | action plan | kaikun02_executor_bridge_v2 |
| kaikun02_executor_bridge_v2 | COO action | 実行橋渡し | kaikun02_actions / proposal updates | active pipeline |
| ai_employee_manager_v1 | dev_proposals | AI社員実績集計 | ai_employee_scores | ai_employee_ranking_v1 |
| ai_employee_ranking_v1 | ai_employee_scores | ランキング計算 | ai_employee_rankings | secretary / kaikun02 quick reply |
| dev_pr_automerge_v1 | merge-ready PR | 自動merge | merged PR | dev_pr_watcher_v1 |
