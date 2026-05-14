# OpenClaw Goal Prompt Template

Use this format for `/goal` requests that may influence long-horizon OpenClaw planning. The goal is read-only planning unless a human explicitly approves a later execution step.

```text
/goal

Goal name:
- <short, stable name>

Source of truth docs:
- <doc path or URL>
- <doc path or URL>

Success criteria:
- <observable outcome>
- <measurable acceptance condition>

Allowed actions:
- Read repository files and docs.
- Read existing runtime state and logs.
- Produce plans, recommendations, patches, docs, and validation reports.
- Run explicitly listed validation commands.

Forbidden actions:
- No launchctl changes.
- No deploy automation.
- No production service restart.
- No automatic router_tasks creation.
- No POST from UI.
- No database writes unless the named existing pipeline already performs that write.
- No credential, token, or secret mutation.

Safety gates:
- Keep the first implementation read-only when unsure.
- Prefer dry-run and simulation over execution.
- Explain the expected value, risk, rollback path, and human approval point before any execution-capable change.
- Separate recommendation from execution.

Validation commands:
- python -m py_compile <changed Python files>
- curl <read-only endpoint>
- git diff --check
- <project-specific dry-run command>

Artifact outputs:
- <docs file>
- <read-only JSON endpoint>
- <digest/report sample>
- <test or validation output>

Human approval points:
- Before enabling writes.
- Before creating or mutating router_tasks automatically.
- Before launchctl, deploy, service restart, or scheduled execution changes.
- Before moving from dry-run execution to limited approved execution.

Rollback criteria:
- Endpoint returns unsafe, misleading, or non-explainable guidance.
- Digest hides critical failures or increases operator ambiguity.
- Validation command fails.
- Any change introduces an unapproved write or execution path.

Expected commit message:
- feat: add long horizon goal prompt and readable digest
```

