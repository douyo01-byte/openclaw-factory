# PRODUCER ENABLE ORDER

## phase1
- proposal_promoter_v1
- spec_refiner_v2
- spec_decomposer_v1

## phase2_safe_audit_first
- proposal_throttle_engine_v1
- learning_result_writer_v1

## phase3_content_generation
- innovation_engine_v1
- strategy_engine_v1
- proposal_builder_loop_v1
- reasoning_engine_v1

## phase4_learning_feedback
- pattern_extractor_v1
- supply_bias_updater_v1

## guard_conditions
- unique open PR count <= 15
- duplicate open pr_url = 0
- closed / merged と pr_status の不整合が増えていない
- guard / watcher / creator が安定
