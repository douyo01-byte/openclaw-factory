# Pre Burn-in Go/No-Go (2026-03-17)

## Judgment
- GO

## Why GO
- canonical DB is unified in practice
- current active runtime is coherent
- mainline pipelines are alive
- open PR count is 0
- source_ai blanks are 0
- stage divergence is 0
- task router smoke passed
- dormant assets are documented and not lost

## Known limitations
- Kaikun02 is not yet a full internal-understanding implementation agent
- secretary_llm_v1 and chat_research_v1 are intentionally held out of current mainline
- team bots are reuse assets, not standalone runtime agents

## Current runtime role split
- Kaikun02 = quick operational responder
- Kaikun04 = deep thinker / structured comparison / long-form reasoning
- innovation_llm_engine_v1 = active proposal generation
- ai_employee_manager/ranking = active scoring layer

## Burn-in objective
- confirm runtime stability without widening scope
- prefer current ACTIVE mainline over restoring dormant flows
- observe queue growth, merge health, and router stability

## Go conditions satisfied
- final sanity pass
- AI employee sanity pass
- router smoke pass
- no open PR backlog
- no immediate DB split detected

## No-Go triggers during burn-in
- repeated DB lock growth on mainline
- router_tasks started/new accumulation without recovery
- open PR backlog reappears and remains uncleared
- proposal stage divergence returns
- canonical DB drift is detected

## Operator policy
- do not restore secretary/chat_research/team standalone bots during burn-in
- keep scope fixed
- only fix failures that affect current ACTIVE mainline

