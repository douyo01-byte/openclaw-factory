# OpenClaw Current State

## 現在地
開発AI:
Lv6〜Lv7

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

## 現在のlive運用判断
- dev_proposals が中核DB
- proposal_state は pending_question 列を含む
- source_ai 空欄の旧履歴は残る
- 本番に近いのは最小系 + 段階起動対象
- producer群は open PR 15 以下維持を条件に再開する

## 現在の open PR 健康条件
- unique open pr_url <= 15 を維持目標
- duplicate open pr_url = 0
- closed / merged と pr_status の不整合を増やさない

## 参照
- docs/08_HANDOVER.md
- docs/10_RUNTIME_AUDIT_STATUS.md
