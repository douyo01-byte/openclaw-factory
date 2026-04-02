
## Routing / Exec Bridge Position (2026-04)

### Routing Layer
- task_router_v1
- inbox_commands → router_tasks の変換
- mode分類（FAST / THINK / DOC / EXEC）
- 現在は独立維持（将来Kaikun統合候補）

### Exec Bridge Layer
- kaikun04_exec_bridge_v1
- Kaikun reply → EXEC抽出 → ops_exec生成
- self_improvement_log連携のため独立維持

### Future Direction
- Kaikunが routing + exec_bridge を内包する形へ進化
- router_tasks の中間層削減を目指す
