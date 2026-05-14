# OpenClaw Long-Horizon Goal

## Active Goal

OpenClawを、稼ぐ能力と稼ぐために必要な能力を継続獲得し、最終的に安全な完全自律運営へ近づく Explainable Operational Intelligence OS に進化させる

## Source Of Truth Docs

- docs/OPENCLAW_LONG_HORIZON_GOAL.md
- docs/OPENCLAW_GOAL_PROMPT_TEMPLATE.md
- docs/06_CURRENT_STATE.md
- docs/10_RUNTIME_AUDIT_STATUS.md
- docs/11_OPERATIONS.md
- docs/DB_WRITE_MAINTENANCE_RULES.md

## Current Phase

Phase 1: observe/read-only intelligence

## Current Focus

n8n/OpenClaw mainline fixation: make the system easier to observe, explain, prioritize, and approve before adding any autonomous execution path.

## Next Best Step

Expose the active goal through read-only planning surfaces and make operator digests compress noisy duplicate signals into clear, approval-gated next actions.

## Blocked By

- Reliable safety gates for writes and execution are not yet proven.
- Operator review and approval queues must be understandable before autonomy expands.
- Runtime noise and duplicate task amplification must be compressed before it can guide work safely.

## Safety Status

Read-only planning is allowed. Autonomous execution, deploy automation, launchctl mutation, automatic router_tasks creation, and UI POST expansion are not allowed for this goal stage.

## Expected Value

Improves OpenClaw's ability to earn by keeping work aligned to revenue capability, making progress explainable, reducing duplicated operational noise, and preserving human approval before execution.

## Staged Roadmap

### Phase 1: observe/read-only intelligence

- Read docs, code, logs, and existing runtime state.
- Produce explainable summaries, risk views, and next-step recommendations.
- No writes except existing approved digest pipelines.

### Phase 2: explainable recommendation

- Recommend one best safe next step with evidence, expected value, and risk.
- Show rejected alternatives and why they were not selected.
- Keep all recommendations reviewable by a human operator.

### Phase 3: approval queue

- Convert recommendations into approval-gated queue items.
- Require explicit human approval before any execution-capable transition.
- Track approval reason, scope, validation, and rollback criteria.

### Phase 4: dry-run execution

- Simulate proposed execution and show expected changes.
- Produce artifacts and validation output without mutating production state.
- Keep dry-run results comparable to the original recommendation.

### Phase 5: limited approved execution

- Execute only narrow, approved, reversible actions.
- Enforce allowlists, validation commands, and rollback criteria.
- Record what changed, why, and which approval authorized it.

### Phase 6: supervised autonomy

- Allow bounded autonomous selection among pre-approved safe actions.
- Keep operator-visible traces, rate limits, and stop conditions.
- Escalate unclear or higher-risk actions back to humans.

### Phase 7: bounded full autonomy

- Operate within explicit business, safety, budget, and technical constraints.
- Preserve explainability, observability, auditability, and emergency stop controls.
- Expand autonomy only after prior phases are reliable in production.

