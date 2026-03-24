# OpenClaw Current State

## 現在の正
- docs単体ではなく docs / DB / runtime 一致状態を正とする
- watcher判定は `~/AI/openclaw-factory-daemon/scripts/check_watcher_health_24h.py` を使う
- watcher は `ops_watcher_events.body` の JSON を唯一のソースとして扱う
- `ops_watcher_events` スキーマは `id / kind / body / created_at`
- private reply 本流は `Telegram -> tg_private_chat_log -> inbox_commands -> secretary_done`

## required targets
- `jp.openclaw.ops_brain_agent_v1`
- `jp.openclaw.private_reply_to_inbox_v1`
- `jp.openclaw.secretary_llm_v1`

## observe targets
- `jp.openclaw.dev_pr_watcher_v1`
- `jp.openclaw.ingest_private_replies_kaikun04`
- `jp.openclaw.db_integrity_watchdog_v1`
- `jp.openclaw.dev_pr_automerge_v1`
- `jp.openclaw.kaikun02_coo_controller_v1`

## live status
- watcher 24h:
  - restarted=0
  - escalations=0
  - notifications=0
  - proposals=0
- health judgement:
  - OK: no restart/escalation/notification/proposal in 24h
  - OK: all required services running

## DB path
- canonical:
  - `~/AI/openclaw-factory/data/openclaw.db`
- daemon link:
  - `~/AI/openclaw-factory-daemon/data/openclaw.db`
  - `-> ~/AI/openclaw-factory/data/openclaw.db`

## runtime実体
- `jp.openclaw.ops_brain_agent_v1`
  - `~/AI/openclaw-factory/scripts/run_ops_brain_agent.sh`
- `jp.openclaw.private_reply_to_inbox_v1`
  - `~/AI/openclaw-factory-daemon/scripts/run_private_reply_to_inbox_v1.sh`
- `jp.openclaw.secretary_llm_v1`
  - LaunchAgent上の `program=/bin/zsh`
