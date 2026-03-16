# Legacy Router / Inbox Candidates

## Current primary path
- task_router_v1
- kaikun02_router_worker_v1
- kaikun04_router_worker_v1
- private_reply_to_inbox_v1
- router_reply_finisher_v1
- router_timeout_watchdog_v1

## Legacy / non-primary candidates
- chat_router_v1.py
- dev_router_v1.py
- tg_inbox_poll_v1.py
- tg_inbox_poll_daemon_v1.py
- scripts/tg_poll_restart.sh

## Verification summary
- no active runtime dependency confirmed from current grep pass
- references found were historical or operational leftovers:
  - archive logs
  - docs / reports / audit
  - past target_system references
  - stop helper script only
- these files should be treated as legacy_or_manual unless a current plist / runner is explicitly reattached

## Note on tg_poll_restart.sh
- targets old label: jp.kuu.openclaw.tg_poll
- kills old poller patterns
- not part of current router / private-reply primary path

## Archive action
- moved to archive/legacy_runtime on 2026-03-16
