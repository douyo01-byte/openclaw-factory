# Secretary Repurpose Spec (2026-03-17)

## Current judgment
- secretary_llm_v1 is not needed in the current quick-route runtime
- current quick operational replies are already covered by kaikun02_router_worker_v1
- restoring secretary_llm_v1 as-is would duplicate responsibility

## Future role
- CEO向け統合要約専任
- quick replyは持たせない
- task_routerの通常経路には入れない
- on-demand summary または scheduled summary 専任にする

## Allowed scope
- OpenClaw全体状況の統合要約
- burn-in前後の状態要約
- CEO向け週次/日次まとめ
- docs / reports / health / ranking / pipeline status の横断要約

## Disallowed scope
- quick route の代替
- Kaikun02 の即答役
- Kaikun04 の deep relay の代替
- proposal 実行本流への直接介入

## Return conditions
- return only if:
  - dedicated input source is defined
  - summary-only responsibility is fixed
  - no overlap with kaikun02 quick routes
  - no overlap with kaikun04 relay thinker

## Recommended implementation shape
- secretary_summary_v2 のような別名で戻すのが安全
- inbox_commands 直読みではなく summary queue / ceo summary request を専用化
- output target is CEO chat only

## Decision
- restore_as_is: no
- repurpose_later: yes
- priority: medium

