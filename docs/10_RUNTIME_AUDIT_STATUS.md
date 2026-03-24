# OpenClaw Runtime Audit Status

## 現 在 の 基 準

- docs正本は live DB / live logs / launchctl / watcher 結果を優先
- ACTIVE本流は promoted tuning observability runtime live 本流
- private reply 本流は healthy を維持

## ACTIVE本 流

### promoted tuning observability runtime live 本 流
- promoted_tuning_observability_runtime_gate_v1
- promoted_tuning_observability_runtime_planner_v1
- apply_promoted_tuning_observability_runtime.sh
- promoted_tuning_observability_runtime_final_gate_v1
- queue_promoted_tuning_observability_runtime_release.sh
- promoted_tuning_observability_runtime_release_planner_v1
- apply_promoted_tuning_observability_runtime_release.sh
- promoted_tuning_observability_runtime_rollout_gate_v1
- queue_promoted_tuning_observability_runtime_rollout.sh
- promoted_tuning_observability_runtime_rollout_planner_v1
- apply_promoted_tuning_observability_runtime_rollout.sh
- promoted_tuning_observability_runtime_rollout_final_gate_v1
- queue_promoted_tuning_observability_runtime_live.sh
- promoted_tuning_observability_runtime_live_planner_v1
- apply_promoted_tuning_observability_runtime_live.sh

### private reply 本 流
- jp.openclaw.private_reply_to_inbox_v1
- jp.openclaw.secretary_llm_v1
- jp.openclaw.ingest_private_replies_kaikun04

## 現 在 の 到 達 点

- proposal 3285 は observability_runtime_live_review_only まで到達済み
- guard_reason は human_review_observability_runtime_live_applied
- observability runtime live applied summary は 1
- latest observability runtime live applied rows に 3285 が出る

## watcher 24h要 約

- ops_watcher_events の 24h 集計は watch のみ
- restarted=[]
- escalations=[]
- notifications=[]
- proposals=[]

## watcher 実 ス キ ー マ

- ops_watcher_events 実カラム:
  - id
  - kind
  - body
  - created_at
- watcher 詳細は body(JSON) を読む
- target 列前提の旧SQLは使わない

## watcher 現 行 対 象

- required:
  - jp.openclaw.ops_brain_agent_v1
  - jp.openclaw.private_reply_to_inbox_v1
  - jp.openclaw.secretary_llm_v1
- observe:
  - jp.openclaw.dev_pr_automerge_v1
  - jp.openclaw.db_integrity_watchdog_v1
  - jp.openclaw.kaikun02_coo_controller_v1
  - jp.openclaw.dev_pr_watcher_v1
  - jp.openclaw.ingest_private_replies_kaikun04

## private reply 健 康 状 態

- pending = 0
- pending older than 5m = 0
- recent inbox / ingest ともに secretary_done 系で安定
- launchctl 上も required 本流は running / active

## cluster bias 状 態

- approved decision spread (normal only)
  - backlog=5
  - execute_now=3
  - archive=1
- approved source spread (normal only)
  - innovation_llm_engine_v1=7
  - cto=1
  - ceo=1
- 直近確認では bias 崩れなし

## Kaikun02参 照 順

1. docs/06_CURRENT_STATE.md
2. docs/08_HANDOVER.md
3. docs/04_KAIKUN04_STARTER.md
