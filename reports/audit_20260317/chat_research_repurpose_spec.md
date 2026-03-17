# Chat Research Repurpose Spec (2026-03-17)

## Current judgment
- chat_research_v1 belongs to older market/business context
- current mainline does not require direct restore
- restoring as-is would reintroduce non-core flow noise

## Future role
- 補助調査専任
- 本流直結しない
- 依頼ベースでのみ使う
- proposal生成の前段補助またはCEO補助調査に限定

## Allowed scope
- product/company/background research
- proposal草案の補助情報収集
- CEO判断用の補足調査
- scout_market_v2 の補助

## Disallowed scope
- main runtime direct insertion
- autonomous high-frequency write loop
- current dev mainline interruption

## Return conditions
- dedicated source table or request queue is defined
- write frequency is throttled
- no direct collision with scout_market_v2 / innovation_llm_engine_v1

## Recommended implementation shape
- chat_research_support_v2 のような別責務名で戻す
- on-demand support only
- optional enrichment worker として扱う

## Decision
- restore_as_is: no
- repurpose_later: yes
- priority: low_to_medium

