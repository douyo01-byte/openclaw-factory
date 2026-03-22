# openclaw-factory
Mac miniでOpenClawを24/7運用するための運用リポジトリ。

提案→PR→自動マージ: Telegramで「提案: <内容>」を送る → dev_proposalsに登録 → 「承認します #<id>」でapproved → PR作成・通知 → マージ後にstatus=mergedへ更新。


## ACTIVE本流
- private reply:
  - ingest_private_replies_kaikun04
  - private_reply_to_inbox_v1
  - secretary_llm_v1
- router:
  - task_router_v1
  - kaikun02_router_worker_v1
  - kaikun04_router_worker_v1
  - router_reply_finisher_v1
- watcher required:
  - jp.openclaw.ops_brain_agent_v1
  - jp.openclaw.private_reply_to_inbox_v1
  - jp.openclaw.secretary_llm_v1


## ACTIVE本 流
- private reply:
  - ingest_private_replies_kaikun04
  - private_reply_to_inbox_v1
  - secretary_llm_v1
- router:
  - task_router_v1
  - kaikun02_router_worker_v1
  - kaikun04_router_worker_v1
  - router_reply_finisher_v1
  - kaikun02_router_cleanup_v1
  - kaikun04_router_cleanup_v1
  - router_stall_watchdog_v1
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
