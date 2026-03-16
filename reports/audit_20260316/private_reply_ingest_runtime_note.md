# PRIVATE REPLY INGEST RUNTIME NOTE 2026-03-16

## active launchagents outside repo
- ~/Library/LaunchAgents/jp.openclaw.ingest_private_replies_kaikun02.plist
- ~/Library/LaunchAgents/jp.openclaw.ingest_private_replies_kaikun04.plist

## repo runners
- scripts/run_ingest_private_replies_v1.sh
- scripts/run_ingest_private_replies_kaikun02.sh
- scripts/run_ingest_private_replies_kaikun04.sh

## verified result
- router_tasks.id=89 -> kaikun02 -> done
- router_tasks.id=88 -> kaikun04 -> done
- tg_private_chat_log ingestion confirmed
