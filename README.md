# openclaw-factory

Mac miniで OpenClawを 24/7運用するための運用リポジトリ。

提案 → PR → 自動マージ:
Telegramで「提案: <内容>」を送る → dev_proposalsに登録
→ 「承認します #<id>」で approved
→ PR作成・通知
→ マージ後に status=merged へ更新。

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

## Private Reply Single Source

    Telegram(private)
    -> tg_private_chat_log
    -> private_reply_to_inbox_v1
    -> inbox_commands
    -> secretary_llm_v1
    -> secretary_done

Legacy router runtimes were archived into archive/router_legacy_20260322 and are not part of the active private reply path.
