## Private Reply Single Source

    Telegram(private)
    -> tg_private_chat_log
    -> private_reply_to_inbox_v1
    -> inbox_commands
    -> secretary_llm_v1
    -> secretary_done

Router runtimes are not part of the private reply mainline.

Excluded runtimes:
- jp.openclaw.task_router_v1
- jp.openclaw.kaikun02_router_worker_v1
- jp.openclaw.kaikun04_router_worker_v1
- jp.openclaw.router_reply_finisher_v1

