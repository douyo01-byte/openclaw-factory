# Telegram Route Policy (2026-04-03)

## Primary
Telegram -> n8n -> api_server -> inbox_commands -> task_router -> kaikun04 -> router_reply_finisher -> ops_exec

Primary launch agents:
- jp.openclaw.api_server
- jp.openclaw.task_router_v1
- jp.openclaw.kaikun04_router_worker_v1
- jp.openclaw.telegram_ops_executor_v1
- jp.openclaw.router_reply_finisher_v1

## Fallback / Legacy
- jp.openclaw.private_reply_to_inbox_v1
- jp.openclaw.ingest_private_replies_kaikun04
- jp.openclaw.secretary_llm_v1
- manual insert

## Policy
- New Telegram ingress should prefer n8n as the primary entrance.
- private_reply / secretary path remains available only as fallback.
- Do not remove fallback until primary has enough burn-in.

## Runtime confirmation
- 2026-04-03: `telegram_n8n` source で end-to-end 完走確認
- inbox_commands id=555 -> router_tasks id=618 (kaikun04 done) -> id=619 (ops_exec done)
- secretary_llm_v1 is not part of the current primary route and should be treated as legacy/fallback

## Next reduction candidate
- secretary_llm_v1 should remain running for now, but operationally treated as observe / fallback candidate
- private_reply_to_inbox_v1 and ingest_private_replies_kaikun04 remain available as emergency fallback
- do not disable fallback until Telegram -> n8n primary has longer burn-in

## Fallback status clarification
- private_reply_to_inbox_v1 is a usable fallback after clearing polluted global DB env
- ingest_private_replies_kaikun04 launch agent currently executes bots/ingest_private_replies_v1.py
- therefore ingest_private_replies_kaikun04 should be treated as legacy-named fallback, not a clean primary candidate

## Operational classification
### Required primary
- jp.openclaw.api_server
- jp.openclaw.task_router_v1
- jp.openclaw.kaikun04_router_worker_v1
- jp.openclaw.telegram_ops_executor_v1
- jp.openclaw.router_reply_finisher_v1

### Usable fallback
- jp.openclaw.private_reply_to_inbox_v1
- manual insert

### Observe / legacy fallback
- jp.openclaw.ingest_private_replies_kaikun04
- jp.openclaw.secretary_llm_v1

## Daily operation
- runtime check:
  `cd ~/AI/openclaw-factory-daemon && ./scripts/check_telegram_route_runtime.sh`
- primary should be treated as required
- usable fallback should remain available
- observe / legacy fallback should not be promoted without explicit review

## Naming policy for legacy fallback
- `jp.openclaw.ingest_private_replies_kaikun04` is legacy-named.
- Current behavior matters more than label cleanliness.
- Rename is deferred until after longer primary burn-in.

## Proposal generation guard
- `bots/dev_proposal_generator_v1.py` で `LEGACY_FALLBACK_TARGETS` を導入
- `bots/ingest_private_replies_v1.py` は primary candidate ではなく legacy fallback target として proposal fallback pool から除外
- 2026-04-03 時点で open proposal の再発は確認されず、3154 は closed のまま
