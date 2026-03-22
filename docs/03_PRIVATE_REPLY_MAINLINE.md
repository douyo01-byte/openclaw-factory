# Private Reply Mainline

## Single Source

    Telegram(private)
    -> tg_private_chat_log
    -> private_reply_to_inbox_v1
    -> inbox_commands
    -> secretary_llm_v1
    -> secretary_done

## Rule
Router runtimes are not part of the active private reply mainline.

Legacy router runtimes were archived into:
- archive/router_legacy_20260322

## Active Components
- ingest_private_replies_kaikun04
- private_reply_to_inbox_v1
- secretary_llm_v1

## Result
- private Telegram -> tg_private_chat_log -> inbox_commands -> secretary_done confirmed
- private reply operates without router_tasks involvement
