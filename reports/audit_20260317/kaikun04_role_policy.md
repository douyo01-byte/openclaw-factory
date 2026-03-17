# Kaikun04 Role Policy (2026-03-17)

## ROLE
- Kaikun04 は THINK / 深い整理 / 長文要約 / 分析タスク担当
- Kaikun04 は relay-only を基本とする
- quick reply は持たせない
- 返信は task_router → kaikun04_router_worker_v1 → Telegram → private reply ingest の流れで処理する

## POSITION
- Kaikun02 = quick reply / COO補助 / 運用即答
- Kaikun04 = THINK / 深い検討 / 長文整理 / 重めの判断材料作成

## CURRENT RULE
- Kaikun04 に dashboard系 quick route は入れない
- 即答が必要なものは Kaikun02 に寄せる
- THINK が必要なものだけ Kaikun04 に流す

## CLEANUP
- stale relay task は kaikun04_router_cleanup_v1 で自動 close
- relay-only 運用を崩す変更を入れる場合は docs/06_CURRENT_STATE.md, docs/08_HANDOVER.md, docs/17_FINAL_UNIFY_DECISION.md を同時更新する

## JUDGMENT
- current Kaikun04 is ACTIVE relay-only thinker
- not a quick-response runtime
