from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = os.environ.get("DB_PATH", str(Path.home() / "AI/openclaw-factory/data/openclaw.db"))
PROMPT_PATH = ROOT / "prompts" / "kaikun04_orchestrator_system.txt"

TASK_TYPES = [
    "code_change",
    "bugfix",
    "deploy",
    "investigation",
    "content_rewrite",
    "lp_optimization",
    "automation_design",
    "runtime_repair",
    "data_update",
    "unknown",
]

OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "objective",
        "task_type",
        "target_system",
        "priority",
        "plan_steps",
        "required_tools",
        "success_criteria",
        "fallback_action",
        "should_execute_now",
        "learn_after_completion",
    ],
    "properties": {
        "objective": {"type": "string"},
        "task_type": {"type": "string", "enum": TASK_TYPES},
        "target_system": {"type": "string"},
        "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
        "plan_steps": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "string"},
        },
        "required_tools": {
            "type": "array",
            "items": {"type": "string"},
        },
        "success_criteria": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "string"},
        },
        "fallback_action": {"type": "string"},
        "should_execute_now": {"type": "boolean"},
        "learn_after_completion": {"type": "boolean"},
    },
}

@dataclass
class PlannerInput:
    task_text: str
    mode: str
    target_system: str
    context: dict[str, Any]

def read_system_prompt() -> str:
    if PROMPT_PATH.exists():
        return PROMPT_PATH.read_text(encoding="utf-8")
    return ""

def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def detect_task_type(task_text: str) -> str:
    t = task_text.lower()

    if any(k in t for k in ["lp", "landing page", "variant", "rewrite", "copy", "cta"]):
        return "lp_optimization"
    if any(k in t for k in ["deploy", "wrangler", "publish", "release", "worker"]):
        return "deploy"
    if any(k in t for k in ["fix", "bug", "error", "exception", "repair", "broken"]):
        return "bugfix"
    if any(k in t for k in ["investigate", "why", "cause", "root cause", "調査", "原因"]):
        return "investigation"
    if any(k in t for k in ["rewrite", "copy", "prompt", "article", "content"]):
        return "content_rewrite"
    if any(k in t for k in ["automation", "orchestrator", "router", "agent", "workflow", "自律", "司令塔"]):
        return "automation_design"
    if any(k in t for k in ["runtime", "launchctl", "daemon", "worker health", "watcher"]):
        return "runtime_repair"
    if any(k in t for k in ["sql", "sqlite", "db", "table", "schema", "data"]):
        return "data_update"
    if any(k in t for k in ["code", "python", "script", "function", "refactor", "implement"]):
        return "code_change"
    return "unknown"

def detect_priority(task_text: str, mode: str) -> str:
    t = task_text.lower()
    m = (mode or "").lower()

    if any(k in t for k in ["urgent", "critical", "fatal", "production down", "blocked", "止まってる", "障害"]):
        return "critical"
    if m in {"deep", "think"}:
        return "high"
    if any(k in t for k in ["autonomous", "orchestrator", "core", "本丸", "中核"]):
        return "high"
    return "medium"

def infer_required_tools(task_type: str, target_system: str, task_text: str) -> list[str]:
    tools: list[str] = []

    if task_type in {"code_change", "bugfix", "automation_design", "runtime_repair"}:
        tools += ["read_repo_files", "write_code", "python_compile", "shell_command"]

    if task_type in {"deploy", "lp_optimization"}:
        tools += ["shell_command", "deploy_script", "runtime_log_check"]

    if task_type in {"data_update", "investigation"}:
        tools += ["sqlite_query"]

    if "openai" in task_text.lower() or "structured outputs" in task_text.lower():
        tools += ["openai_api"]

    if "router" in task_text.lower() or "ops_exec" in task_text.lower():
        tools += ["router_tasks_db"]

    if target_system:
        tools.append(f"target:{target_system}")

    deduped: list[str] = []
    seen: set[str] = set()
    for x in tools:
        if x not in seen:
            seen.add(x)
            deduped.append(x)
    return deduped or ["read_repo_files"]

def build_plan_steps(task_type: str, target_system: str, task_text: str) -> list[str]:
    steps: list[str] = []

    if task_type == "automation_design":
        steps = [
            "Inspect relevant runtime files, DB tables, and existing workers connected to the requested system.",
            "Define fixed JSON output contract, planner boundaries, and handoff points to existing execution systems.",
            "Implement a minimal orchestrator skeleton with pluggable planner backend and deterministic fallback planner.",
            "Add a runnable shell script and sample task execution path.",
            "Compile and run sample tasks, then verify JSON shape and downstream compatibility.",
        ]
    elif task_type == "lp_optimization":
        steps = [
            "Read latest LP judge, rewriter, and metrics paths currently in production.",
            "Map current LP improvement loop and isolate where Kaikun04 should take ownership.",
            "Implement structured planning output for rewrite, judge, deploy, and learn steps.",
            "Run sample LP planning task and verify output is actionable.",
        ]
    elif task_type == "bugfix":
        steps = [
            "Reproduce or localize the bug from logs, code path, or failing command.",
            "Patch the smallest safe area without breaking the mainline.",
            "Compile and execute the affected flow.",
            "Record fallback and learning hooks for recurrence prevention.",
        ]
    else:
        steps = [
            "Inspect the relevant code and runtime context.",
            "Convert the request into a fixed execution plan with explicit success criteria.",
            "Run the smallest safe validation step.",
            "Record learnable signals after completion.",
        ]

    if target_system and all(target_system not in s for s in steps):
        steps.insert(1, f"Focus implementation on target system: {target_system}.")
    return steps

def build_success_criteria(task_type: str, target_system: str) -> list[str]:
    base = [
        "Output is valid JSON matching the orchestrator schema.",
        "Plan steps are concrete enough to execute without extra interpretation.",
        "Required tools and success criteria are explicitly listed.",
    ]

    if task_type == "automation_design":
        base += [
            "Planner skeleton can run locally and return a deterministic JSON plan.",
            "Result can be saved to stdout and optionally to the database.",
            "Design is easy to connect later to task_router, router_tasks, and ops_exec.",
        ]

    if target_system:
        base.append(f"Plan is aligned to target system: {target_system}.")

    return base

def should_execute_now(task_type: str, task_text: str) -> bool:
    t = task_text.lower()
    if any(k in t for k in ["design", "skeleton", "骨組み", "最小実装", "plan", "orchestrator"]):
        return True
    if task_type in {"bugfix", "runtime_repair", "lp_optimization", "automation_design", "code_change"}:
        return True
    return False

def build_fallback_action(task_type: str, target_system: str) -> str:
    if task_type == "automation_design":
        return "Return deterministic heuristic plan, save it, and stop before any destructive execution."
    if task_type == "deploy":
        return "Skip deploy, print validation summary, and keep current production runtime unchanged."
    if task_type == "bugfix":
        return "Abort after compile or runtime failure and print the smallest failing step with file path."
    if target_system:
        return f"Defer execution and emit a validation-only plan for {target_system}."
    return "Emit validation-only plan and wait for the next safe execution step."

def heuristic_plan(inp: PlannerInput) -> dict[str, Any]:
    task_text = normalize_space(inp.task_text)
    task_type = detect_task_type(task_text)
    priority = detect_priority(task_text, inp.mode)
    target_system = inp.target_system or "unknown"

    plan = {
        "objective": task_text,
        "task_type": task_type,
        "target_system": target_system,
        "priority": priority,
        "plan_steps": build_plan_steps(task_type, target_system, task_text),
        "required_tools": infer_required_tools(task_type, target_system, task_text),
        "success_criteria": build_success_criteria(task_type, target_system),
        "fallback_action": build_fallback_action(task_type, target_system),
        "should_execute_now": should_execute_now(task_type, task_text),
        "learn_after_completion": True,
    }
    validate_plan(plan)
    return plan

def validate_plan(plan: dict[str, Any]) -> None:
    required = OUTPUT_SCHEMA["required"]
    for key in required:
        if key not in plan:
            raise ValueError(f"missing_required_key={key}")

    if plan["task_type"] not in TASK_TYPES:
        raise ValueError(f"invalid_task_type={plan['task_type']}")

    if plan["priority"] not in {"low", "medium", "high", "critical"}:
        raise ValueError(f"invalid_priority={plan['priority']}")

    for key in ("plan_steps", "required_tools", "success_criteria"):
        if not isinstance(plan[key], list) or not plan[key]:
            raise ValueError(f"invalid_nonempty_list={key}")

    if not isinstance(plan["should_execute_now"], bool):
        raise ValueError("should_execute_now_must_be_bool")

    if not isinstance(plan["learn_after_completion"], bool):
        raise ValueError("learn_after_completion_must_be_bool")

def build_openai_messages(system_prompt: str, inp: PlannerInput) -> list[dict[str, str]]:
    payload = {
        "task_text": inp.task_text,
        "mode": inp.mode,
        "target_system": inp.target_system,
        "context": inp.context,
        "required_output_schema": OUTPUT_SCHEMA,
    }
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]

def maybe_openai_plan(inp: PlannerInput) -> tuple[str, dict[str, Any]]:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("OPENAI_MODEL", "gpt-5")
    backend = os.environ.get("KAIKUN04_ORCHESTRATOR_BACKEND", "heuristic").strip().lower()
    system_prompt = read_system_prompt()

    if backend != "openai" or not api_key:
        return "heuristic", heuristic_plan(inp)

    try:
        from openai import OpenAI
    except Exception:
        return "heuristic", heuristic_plan(inp)

    client = OpenAI(api_key=api_key)
    messages = build_openai_messages(system_prompt, inp)

    try:
        resp = client.responses.create(
            model=model,
            input=messages,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "kaikun04_orchestrator_plan",
                    "schema": OUTPUT_SCHEMA,
                    "strict": True,
                }
            },
        )
        raw = getattr(resp, "output_text", "") or ""
        plan = json.loads(raw)
        validate_plan(plan)
        return "openai", plan
    except Exception:
        return "heuristic", heuristic_plan(inp)

def save_plan(db_path: str, task_text: str, mode: str, target_system: str, context: dict[str, Any], backend: str, plan: dict[str, Any]) -> int:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute(
        """
        create table if not exists kaikun04_orchestrator_runs (
          id integer primary key autoincrement,
          task_text text not null,
          mode text,
          target_system text,
          context_json text,
          planner_backend text not null default 'heuristic',
          plan_json text not null,
          created_at text not null default (datetime('now'))
        )
        """
    )
    cur.execute(
        """
        insert into kaikun04_orchestrator_runs
        (task_text, mode, target_system, context_json, planner_backend, plan_json)
        values (?, ?, ?, ?, ?, ?)
        """,
        (
            task_text,
            mode,
            target_system,
            json.dumps(context, ensure_ascii=False),
            backend,
            json.dumps(plan, ensure_ascii=False),
        ),
    )
    run_id = int(cur.lastrowid)
    con.commit()
    con.close()
    return run_id

def emit_router_task(db_path: str, mode: str, task_text: str, plan: dict[str, Any]) -> int:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute(
        """
        insert into router_tasks
        (source_command_id, mode, target_bot, task_text, status, created_at, updated_at, reply_text, result_text)
        values
        (0, ?, 'kaikun04', ?, 'new', datetime('now'), datetime('now'), '', ?)
        """,
        (
            mode,
            task_text,
            json.dumps(plan, ensure_ascii=False),
        ),
    )
    task_id = int(cur.lastrowid)
    con.commit()
    con.close()
    return task_id

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--task-text", required=True)
    p.add_argument("--mode", default="THINK")
    p.add_argument("--target-system", default="openclaw")
    p.add_argument("--context-json", default="{}")
    p.add_argument("--save-db", action="store_true")
    p.add_argument("--emit-router-task", action="store_true")
    p.add_argument("--db-path", default=DEFAULT_DB_PATH)
    p.add_argument("--pretty", action="store_true")
    return p.parse_args()

def main() -> None:
    args = parse_args()

    try:
        context = json.loads(args.context_json)
        if not isinstance(context, dict):
            raise ValueError("context_json must decode to object")
    except Exception as e:
        raise SystemExit(f"invalid_context_json err={e!r}")

    inp = PlannerInput(
        task_text=args.task_text,
        mode=args.mode,
        target_system=args.target_system,
        context=context,
    )
    backend, plan = maybe_openai_plan(inp)

    output: dict[str, Any] = {
        "planner_backend": backend,
        "plan": plan,
    }

    if args.save_db:
        run_id = save_plan(
            db_path=args.db_path,
            task_text=args.task_text,
            mode=args.mode,
            target_system=args.target_system,
            context=context,
            backend=backend,
            plan=plan,
        )
        output["run_id"] = run_id

    if args.emit_router_task:
        router_task_id = emit_router_task(
            db_path=args.db_path,
            mode=args.mode,
            task_text=args.task_text,
            plan=plan,
        )
        output["router_task_id"] = router_task_id

    if args.pretty:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(output, ensure_ascii=False))

if __name__ == "__main__":
    main()
