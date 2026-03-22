# OpenClaw Docs Index

## Core Entry
- 01_SINGLE_SOURCE_OF_TRUTH.md
- 02_ROLE_REGISTRY.md
- 03_KAIKUN04_RUNTIME_RULE.md
- 04_KAIKUN04_STARTER.md
- 05_MAINLINE_IMPLEMENTATION_GATE.md
- 06_META_KEEP_HOLD.md
- 07_BUSINESS_KEEP_HOLD.md
- 09_BUSINESS_MAINLINE_REDESIGN.md
- 10_BUSINESS_INTEGRATION_DECISION.md
- 11_BUSINESS_FUNCTION_EXTRACTION_PLAN.md
- 15_BUSINESS_MAINLINE_FILE_MAP.md
- 16_BUSINESS_FUNCTION_ASSIGNMENT.md
- 18_BUSINESS_ABSORB_CONFIRMED.md

## 核ドキュメント
- 03_PRIVATE_REPLY_MAINLINE.md
- 06_CURRENT_STATE.md
- 08_HANDOVER.md
- 12_RUNTIME_CLASSIFICATION.md
- 13_LAUNCHAGENT_INVENTORY.md
- 14_LEGACY_TRIAGE.md

## 運用
- 17_EFFICIENCY_RULES.md

## docs修正注意
- スマホ編集後は spacing 崩れを確認する
- 存在しない参照を index に残さない
- runtime に関する判断は docs 単独で行わない

## ACTIVE本流
- private reply:
  - ingest_private_replies_kaikun04
  - private_reply_to_inbox_v1
  - secretary_llm_v1
- watcher required:
  - jp.openclaw.ops_brain_agent_v1
  - jp.openclaw.private_reply_to_inbox_v1
  - jp.openclaw.secretary_llm_v1
- watcher observe:
  - jp.openclaw.dev_pr_automerge_v1
  - jp.openclaw.db_integrity_watchdog_v1
  - jp.openclaw.kaikun02_coo_controller_v1
  - jp.openclaw.dev_pr_watcher_v1
  - jp.openclaw.ingest_private_replies_kaikun04
