# OpenClaw Runtime Audit Status

## 現在の基準
- 正は docs / DB / runtime 一致状態
- watcher判定は `scripts/check_watcher_health_24h.py` を使用
- watcher event source は `ops_watcher_events.body` JSON
- `ops_watcher_events` schema:
  - `id`
  - `kind`
  - `body`
  - `created_at`

## required
- `jp.openclaw.ops_brain_agent_v1`
- `jp.openclaw.private_reply_to_inbox_v1`
- `jp.openclaw.secretary_llm_v1`

## observe
- `jp.openclaw.dev_pr_watcher_v1`
- `jp.openclaw.ingest_private_replies_kaikun04`
- `jp.openclaw.db_integrity_watchdog_v1`
- `jp.openclaw.dev_pr_automerge_v1`
- `jp.openclaw.kaikun02_coo_controller_v1`

## live status
- watcher 24h summary:
  - restarted=0
  - escalations=0
  - notifications=0
  - proposals=0
- health judgement:
  - OK: no restart/escalation/notification/proposal in 24h
  - OK: all required services running

## live runtime paths
- `jp.openclaw.ops_brain_agent_v1`
  - plist: `~/Library/LaunchAgents/jp.openclaw.ops_brain_agent_v1.plist`
  - program: `~/AI/openclaw-factory/scripts/run_ops_brain_agent.sh`
- `jp.openclaw.private_reply_to_inbox_v1`
  - plist: `~/Library/LaunchAgents/jp.openclaw.private_reply_to_inbox_v1.plist`
  - program: `~/AI/openclaw-factory-daemon/scripts/run_private_reply_to_inbox_v1.sh`
- `jp.openclaw.secretary_llm_v1`
  - plist: `~/Library/LaunchAgents/jp.openclaw.secretary_llm_v1.plist`
  - program: `/bin/zsh`

## DB path
- canonical:
  - `~/AI/openclaw-factory/data/openclaw.db`
- daemon link:
  - `~/AI/openclaw-factory-daemon/data/openclaw.db`
  - `-> ~/AI/openclaw-factory/data/openclaw.db`

## notes
- `jp.openclaw.db_integrity_watchdog_v1` は observe で `observed_stopped=True`
- `jp.openclaw.dev_pr_automerge_v1` は `exists=False`
- `jp.openclaw.kaikun02_coo_controller_v1` は `exists=False`
