# OpenClaw Brain

OpenClaw agents must prefer runtime truth over assumptions:

- Read the relevant code, logs, database rows, and smoke results before deciding.
- Keep changes minimal and local to the requested behavior.
- Preserve existing runtime contracts unless a task explicitly asks to change them.
- Run the narrowest meaningful smoke test before marking a task ready for review.
- Do not commit, push, deploy, or edit launchctl configuration unless the current task explicitly asks for it.
- Save blockers and evidence in the task result instead of guessing.
