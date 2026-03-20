# OpenClaw Runtime Audit Status

## 現在の基準
- docs正本復元元: dev/self-watch-recovery

## 実働最小系
- open_pr_guard_v1
- dev_pr_watcher_v1
- dev_pr_creator_v1

## 段階起動対象
- proposal_promoter_v1
- spec_refiner_v2
- spec_decomposer_v1

## 要監査
- innovation_engine_v1
- strategy_engine_v1
- proposal_builder_loop_v1
- reasoning_engine_v1
- proposal_throttle_engine_v1
- learning_result_writer_v1
- pattern_extractor_v1
- supply_bias_updater_v1

## producer再開条件
- unique open PR count <= 15
- duplicate open pr_url = 0
- closed / merged と pr_status の不整合が増えていない
- creator / watcher / guard の3点が安定

## Kaikun02参照順
1. docs/06_CURRENT_STATE.md
2. docs/08_HANDOVER.md
3. docs/04_KAIKUN04_STARTER.md
