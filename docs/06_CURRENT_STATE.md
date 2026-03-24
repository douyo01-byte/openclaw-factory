# OpenClaw Current State

## 現在地

開発AI:
Lv6〜Lv7

## ACTIVE本流

### promoted tuning observability runtime live 本流
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

### private reply 本流
- jp.openclaw.private_reply_to_inbox_v1
- jp.openclaw.secretary_llm_v1
- jp.openclaw.ingest_private_replies_kaikun04

## 現在の到達点

- proposal 3285 は observability_runtime_live_review_only まで到達済み
- guard_reason は human_review_observability_runtime_live_applied
- observability runtime live applied summary は 1
- latest observability runtime live applied rows に 3285 が出る

## watcher 24h要約

- ops_watcher_events の 24h 集計は watch のみ
- restarted=[]
- escalations=[]
- notifications=[]
- proposals=[]
- required 対象の private_reply_to_inbox_v1 / secretary_llm_v1 は稼働継続
- observe 対象の dev_pr_automerge_v1 / db_integrity_watchdog_v1 / kaikun02_coo_controller_v1 は observed_stopped 扱い

## private reply 健康状態

- pending = 0
- pending older than 5m = 0
- recent inbox / ingest ともに secretary_done 系で安定
- launchctl 上も required 本流は running / active

## cluster bias 状態

- approved decision spread (normal only)
  - backlog=5
  - execute_now=3
  - archive=1
- approved source spread (normal only)
  - innovation_llm_engine_v1=7
  - cto=1
  - ceo=1
- 直近確認では bias 崩れなし

## watcher 実スキーマ

- ops_watcher_events 実カラム:
  - id
  - kind
  - body
  - created_at
- watcher 詳細は body(JSON) を読む
- target 列前提の旧SQLは使わない

## 参照

- docs/08_HANDOVER.md
- docs/10_RUNTIME_AUDIT_STATUS.md
