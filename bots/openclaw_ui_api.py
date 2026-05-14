from typing import Any, Optional
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO
try:
    from fastapi import FastAPI, Query
    from pydantic import BaseModel
    from fastapi.responses import JSONResponse, FileResponse, Response
    from fastapi.staticfiles import StaticFiles
except ModuleNotFoundError:
    def Query(default=None, **_kwargs):
        return default

    class BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    class Response:
        def __init__(self, content="", media_type=None):
            self.content = content
            self.media_type = media_type

    class JSONResponse(dict):
        pass

    class FileResponse:
        def __init__(self, path):
            self.path = path

    class StaticFiles:
        def __init__(self, directory):
            self.directory = directory

    class FastAPI:
        def __init__(self, title=""):
            self.title = title

        def get(self, *_args, **_kwargs):
            return lambda fn: fn

        def post(self, *_args, **_kwargs):
            return lambda fn: fn

        def mount(self, *_args, **_kwargs):
            return None

        async def __call__(self, scope, receive, send):
            body = b"fastapi dependency missing"
            await send({
                "type": "http.response.start",
                "status": 503,
                "headers": [(b"content-type", b"text/plain")],
            })
            await send({"type": "http.response.body", "body": body})
import datetime
import os
import sqlite3
import sys

DB_PATH = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
BOT_DIR = Path(__file__).resolve().parent
if str(BOT_DIR) not in sys.path:
    sys.path.insert(0, str(BOT_DIR))

app = FastAPI(title="OpenClaw UI API")


def connect_db() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    return c


def table_exists(c: sqlite3.Connection, table: str) -> bool:
    row = c.execute(
        "select 1 from sqlite_master where type='table' and name=?",
        (table,),
    ).fetchone()
    return row is not None


def table_columns(c: sqlite3.Connection, table: str) -> set[str]:
    if not table_exists(c, table):
        return set()
    return {str(r["name"]) for r in c.execute(f"pragma table_info({table})").fetchall()}


def rows(c: sqlite3.Connection, sql: str, args=()):
    return [dict(r) for r in c.execute(sql, args).fetchall()]


class LocalOpenClawDBAdapter:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_router_tasks(self):
        with connect_db() as c:
            if not table_exists(c, "router_tasks"):
                return []
            order = "id desc" if "id" in table_columns(c, "router_tasks") else "rowid desc"
            return rows(c, f"select * from router_tasks order by {order} limit 1000")

    def get_parent_child_relations(self):
        with connect_db() as c:
            if not table_exists(c, "router_tasks"):
                return []
            cols = table_columns(c, "router_tasks")
            if not {"id", "parent_task_id"}.issubset(cols):
                return []
            return rows(
                c,
                """
                select parent_task_id as parent_id, id as child_id
                from router_tasks
                where parent_task_id is not null
                order by parent_task_id desc, id desc
                limit 1000
                """,
            )

    def get_execs(self):
        with connect_db() as c:
            if not table_exists(c, "router_tasks"):
                return []
            cols = table_columns(c, "router_tasks")
            if "mode" not in cols:
                return []
            return rows(
                c,
                """
                select *
                from router_tasks
                where coalesce(mode,'')='EXEC'
                   or coalesce(target_bot,'')='ops_exec'
                order by id desc
                limit 1000
                """,
            )

    def get_logs(self, task_id: Optional[int] = None, limit: int = 100):
        with connect_db() as c:
            for table in ("router_task_logs", "task_logs", "logs"):
                if not table_exists(c, table):
                    continue
                cols = table_columns(c, table)
                where = ""
                args: list[object] = []
                if task_id is not None:
                    if "task_id" in cols:
                        where = "where task_id=?"
                        args.append(task_id)
                    elif "router_task_id" in cols:
                        where = "where router_task_id=?"
                        args.append(task_id)
                order = "id desc" if "id" in cols else "rowid desc"
                args.append(limit)
                return rows(c, f"select * from {table} {where} order by {order} limit ?", args)
            return []

    def get_artifacts(self, task_id: Optional[int] = None):
        with connect_db() as c:
            for table in ("router_task_artifacts", "task_artifacts", "artifacts"):
                if not table_exists(c, table):
                    continue
                cols = table_columns(c, table)
                where = ""
                args: list[object] = []
                if task_id is not None:
                    if "task_id" in cols:
                        where = "where task_id=?"
                        args.append(task_id)
                    elif "router_task_id" in cols:
                        where = "where router_task_id=?"
                        args.append(task_id)
                order = "id desc" if "id" in cols else "rowid desc"
                return rows(c, f"select * from {table} {where} order by {order} limit 1000", args)
            return []

    def get_capabilities(self):
        with connect_db() as c:
            for table in ("capability_registry", "capabilities"):
                if not table_exists(c, table):
                    continue
                cols = table_columns(c, table)
                order = "id desc" if "id" in cols else "rowid desc"
                return rows(c, f"select * from {table} order by {order} limit 1000")
            return []


def adapter() -> LocalOpenClawDBAdapter:
    return LocalOpenClawDBAdapter(DB_PATH)

@app.get("/")
def root():
    html = open("ui/index.html", encoding="utf-8").read()
    return Response(content=html, media_type="text/html")

app.mount("/ui", StaticFiles(directory="ui"), name="ui")

@app.get("/health")
def health():
    return {"ok": True, "db_path": DB_PATH}


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def render_text(fn, *args) -> str:
    buf = StringIO()
    with redirect_stdout(buf):
        fn(*args)
    return buf.getvalue().strip()


def report_response(report: str, **extra):
    data = {
        "ok": True,
        "report": report,
        "generated_at": now_iso(),
    }
    data.update(extra)
    return data


def dataclass_like(value: Any) -> dict[str, Any]:
    if hasattr(value, "__dataclass_fields__"):
        return {key: getattr(value, key) for key in value.__dataclass_fields__}
    if isinstance(value, dict):
        return value
    return {}


def compact_loop_summary(loop: dict[str, Any]) -> dict[str, Any]:
    health = loop.get("health", {})
    root = loop.get("root", {})
    hotspot = loop.get("hotspot", {})
    return {
        "status": loop.get("current_mode", "unknown"),
        "loop_state": loop.get("loop_state", "unknown"),
        "health_score": health.get("health_score", 0),
        "instability_score": health.get("instability_score", 0),
        "deferred_backlog": health.get("deferred_backlog", 0),
        "retry_pressure": health.get("retry_pressure", 0),
        "top_risk": loop.get("top_risk", "unknown"),
        "root_cause": root.get("label", "unknown"),
        "root_confidence": root.get("confidence", 0),
        "root_chain": loop.get("root_chain", []),
        "root_chain_score": loop.get("root_chain_score", 0),
        "hotspot": hotspot.get("label", "unknown"),
        "best_safe_remediation": loop.get("best_safe_remediation", ""),
        "projected_health_gain": loop.get("projected_health_gain", 0),
        "actions": loop.get("actions", []),
        "watchlist": loop.get("watchlist", []),
        "simulation_outcomes": loop.get("simulation_outcomes", []),
        "historical_note": loop.get("historical_note", ""),
        "decision_trace": loop.get("decision_trace", []),
        "memory_source": loop.get("memory_source", "unknown"),
        "operational_memory_update_plan": loop.get("operational_memory_update_plan", {}),
    }


def compact_plan_summary(plan: Any) -> dict[str, Any]:
    return {
        "planning_horizon": plan.horizon,
        "planning_mode": plan.planning_mode,
        "sustainability_score": plan.sustainability_score,
        "recurrence_risk": plan.recurrence_risk,
        "recurrence_risk_score": plan.recurrence_risk_score,
        "maintenance_pressure": plan.maintenance_pressure,
        "maintenance_pressure_score": plan.maintenance_pressure_score,
        "operator_load": plan.operator_load,
        "operator_load_score": plan.operator_load_score,
        "stability_projection": plan.stability_projection,
        "stability_projection_score": plan.stability_projection_score,
        "dominant_long_term_risk": plan.dominant_long_term_risk,
        "recommended_long_horizon_focus": plan.recommended_long_horizon_focus,
        "anti_patterns": plan.anti_patterns,
        "supporting_signals": plan.supporting_signals,
        "scoring_examples": plan.scoring_examples,
    }


@app.get("/api/dev-autopilot/compact")
def dev_autopilot_compact():
    from dev_autopilot_executive_report_v1 import build_report, print_compact

    report = build_report(DB_PATH)
    plan = compact_plan_summary(report["plan"])
    return report_response(
        render_text(print_compact, report),
        summary={
            "status": report["status"],
            "health": report["overall_health"],
            "top_risk": report["top_risk"],
            "root_cause": report["root_cause"],
            "root_chain": report["loop"].get("root_chain", []),
            "selected_policy": report["selected_policy"],
            "best_safe_next_action": report["best_safe_next_action"],
            "sustainability_score": plan["sustainability_score"],
            "do_not_do": [
                "no launchctl",
                "no deploy",
                "no git push",
                "no executable router_tasks",
                "no auto Codex",
            ],
        },
        loop=compact_loop_summary(report["loop"]),
        plan=plan,
    )


@app.get("/api/dev-autopilot/report")
def dev_autopilot_report():
    from dev_autopilot_executive_report_v1 import build_report, print_report

    report = build_report(DB_PATH)
    return report_response(
        render_text(print_report, report),
        summary={
            "status": report["status"],
            "health": report["overall_health"],
            "top_risk": report["top_risk"],
            "root_cause": report["root_cause"],
            "root_chain": report["loop"].get("root_chain", []),
            "selected_policy": report["selected_policy"],
            "best_safe_next_action": report["best_safe_next_action"],
            "sustainability_score": report["plan"].sustainability_score,
            "do_not_do": [
                "no launchctl",
                "no deploy",
                "no git push",
                "no executable router_tasks",
                "no auto Codex",
            ],
        },
    )


@app.get("/api/dev-autopilot/policy")
def dev_autopilot_policy():
    from dev_autopilot_policy_v1 import print_policy, select_policy

    policy = select_policy(DB_PATH)
    selected = policy["selected"]
    return report_response(
        render_text(print_policy, policy),
        selected_policy=selected.policy_name,
        selection_confidence=selected.selection_confidence,
        summary={
            "selected_policy": selected.policy_name,
            "selection_confidence": selected.selection_confidence,
            "selection_reason": selected.selection_reason,
            "supporting_signals": selected.supporting_signals,
            "expected_behavior": selected.expected_behavior,
            "policy_scores": [dataclass_like(score) for score in policy["scores"]],
            "transitions": policy["transitions"],
            "history_source": policy["history_source"],
        },
    )


@app.get("/api/dev-autopilot/loop")
def dev_autopilot_loop():
    from dev_autopilot_loop_v1 import build_loop, print_summary

    loop = build_loop(DB_PATH)
    return report_response(
        render_text(print_summary, loop),
        current_mode=loop["current_mode"],
        loop_state=loop["loop_state"],
        top_risk=loop["top_risk"],
        summary=compact_loop_summary(loop),
    )


@app.get("/api/dev-autopilot/risks")
def dev_autopilot_risks():
    from dev_autopilot_planning_v1 import build_plan, print_plan

    plan = build_plan(DB_PATH, "7d")
    return report_response(
        render_text(print_plan, plan),
        planning_horizon=plan.horizon,
        sustainability_score=plan.sustainability_score,
        recurrence_risk=plan.recurrence_risk,
        dominant_long_term_risk=plan.dominant_long_term_risk,
        summary=compact_plan_summary(plan),
    )


@app.get("/api/dev-autopilot/memory")
def dev_autopilot_memory():
    from dev_autopilot_memory_v1 import group_patterns, load_incidents, print_patterns

    incidents, source = load_incidents(DB_PATH)
    patterns = group_patterns(incidents)
    return report_response(
        render_text(print_patterns, patterns, source),
        summary={
            "source": source,
            "incident_count": len(incidents),
            "patterns": patterns[:8],
        },
    )


class TaskCreate(BaseModel):
    target_bot: str = "kaikun04"
    mode: str = "THINK"
    task_role: str = ""
    parent_task_id: int | None = None
    task_text: str



class TaskAction(BaseModel):
    action: str
    target_bot: str = "kaikun04"
    mode: str = "THINK"

@app.post("/api/tasks")
def create_task(payload: TaskCreate):
    import sqlite3
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    c.execute("""
        insert into router_tasks(
          source_command_id, parent_task_id, task_role, mode, target_bot, task_text, status, created_at, updated_at
        ) values(
          0, ?, ?, ?, ?, ?, 'new', datetime('now'), datetime('now')
        )
    """, (
        payload.parent_task_id,
        payload.task_role or "",
        payload.mode,
        payload.target_bot,
        payload.task_text
    ))
    new_id = c.execute("select last_insert_rowid()").fetchone()[0]
    c.commit()
    c.close()
    return {"ok": True, "id": new_id}


class ExecCreate(BaseModel):
    script: str
    args: str = ""

@app.post("/api/exec")
def create_exec(payload: ExecCreate):
    import sqlite3
    allowed = {
        "db_health.sh",
        "git_status.sh",
        "status_core.sh",
        "kick_service.sh",
        "route_smoke.sh",
        "gh_pr_create.sh",
        "gh_pr_merge.sh",
        "git_commit_push.sh",
        "restart_service.sh",
        "fix_db.sh",
        "deploy_safe.sh",
        "run_python.sh",
        "log_check.sh"
    }
    script = (payload.script or "").strip()
    args = (payload.args or "").strip()
    if script not in allowed:
        return {"ok": False, "error": "script_not_allowed"}
    task_text = f"[EXEC]\nscript={script}"
    if args:
        task_text += f"\narg={args}"
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.execute("pragma busy_timeout=30000")
    c.execute("""
        insert into router_tasks(
          source_command_id, parent_task_id, task_role, mode, target_bot, task_text, status, created_at, updated_at
        ) values(
          0, null, '', 'EXEC', 'ops_exec', ?, 'new', datetime('now'), datetime('now')
        )
    """, (task_text,))
    new_id = c.execute("select last_insert_rowid()").fetchone()[0]
    c.commit()
    c.close()
    return {"ok": True, "id": new_id, "task_text": task_text}

@app.get("/api/tasks")
def tasks(limit: int = Query(100, ge=1, le=1000)):
    rows = adapter().get_router_tasks()
    rows = sorted(rows, key=lambda x: x.get("id", 0), reverse=True)[:limit]
    return {"count": len(rows), "items": rows}

@app.get("/api/relations")
def relations():
    rows = adapter().get_parent_child_relations()
    return {"count": len(rows), "items": rows}

@app.get("/api/execs")
def execs(limit: int = Query(100, ge=1, le=1000)):
    rows = adapter().get_execs()[:limit]
    return {"count": len(rows), "items": rows}

@app.get("/api/logs")
def logs(task_id: Optional[int] = None, limit: int = Query(100, ge=1, le=1000)):
    rows = adapter().get_logs(task_id=task_id, limit=limit)
    return {"count": len(rows), "items": rows}

@app.get("/api/artifacts")
def artifacts(task_id: Optional[int] = None):
    rows = adapter().get_artifacts(task_id=task_id)
    return {"count": len(rows), "items": rows}

@app.get("/api/capabilities")
def capabilities():
    rows = adapter().get_capabilities()
    return {"count": len(rows), "items": rows}



@app.get("/api/tmp_exec")
def tmp_exec(limit: int = Query(50, ge=1, le=200)):
    root = Path("/Users/doyopc/AI/openclaw-factory-daemon/tmp_exec")
    items = []
    if root.exists():
        for f in sorted(root.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
            try:
                items.append({
                    "name": f.name,
                    "size": f.stat().st_size,
                    "mtime": int(f.stat().st_mtime),
                    "content": f.read_text(encoding="utf-8", errors="ignore")[:2000]
                })
            except Exception as e:
                items.append({
                    "name": f.name,
                    "size": 0,
                    "mtime": 0,
                    "content": f"read_error:{e!r}"
                })
    return {"count": len(items), "items": items}

@app.get("/api/summary")
def summary():
    a = adapter()
    data = {
        "router_tasks": len(a.get_router_tasks()),
        "relations": len(a.get_parent_child_relations()),
        "execs": len(a.get_execs()),
        "artifacts": len(a.get_artifacts()),
        "capabilities": len(a.get_capabilities()),
    }
    return JSONResponse(data)


@app.post("/api/tasks/{task_id}/exec")
def force_exec(task_id: int):
    import sqlite3
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.execute("pragma busy_timeout=30000")

    c.execute("""
        update router_tasks
        set status='new',
            updated_at=datetime('now')
        where id=?
    """, (task_id,))

    c.commit()
    c.close()
    return {"ok": True, "task_id": task_id}


@app.post("/api/tasks/{task_id}/action")
def task_action(task_id: int, payload: TaskAction):
    import sqlite3
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")

    row = c.execute("""
        select *
        from router_tasks
        where id=?
    """, (task_id,)).fetchone()

    if not row:
        c.close()
        return {"ok": False, "error": "not_found", "task_id": task_id}

    action = (payload.action or "").strip().lower()

    if action == "cancel":
        c.execute("""
            update router_tasks
            set status='cancelled',
                updated_at=datetime('now')
            where id=?
        """, (task_id,))
        c.commit()
        c.close()
        return {"ok": True, "action": action, "task_id": task_id}

    if action == "rerun":
        c.execute("""
            update router_tasks
            set status='new',
                updated_at=datetime('now')
            where id=?
        """, (task_id,))
        c.commit()
        c.close()
        return {"ok": True, "action": action, "task_id": task_id}

    if action == "duplicate":
        c.execute("""
            insert into router_tasks(
              source_command_id, parent_task_id, task_role, mode, target_bot, task_text, status, created_at, updated_at
            ) values(
              ?, ?, ?, ?, ?, ?, 'new', datetime('now'), datetime('now')
            )
        """, (
            row["source_command_id"] or 0,
            row["parent_task_id"],
            row["task_role"] or "",
            payload.mode or row["mode"] or "THINK",
            payload.target_bot or row["target_bot"] or "kaikun04",
            row["task_text"] or ""
        ))
        new_id = c.execute("select last_insert_rowid()").fetchone()[0]
        c.commit()
        c.close()
        return {"ok": True, "action": action, "task_id": task_id, "new_id": new_id}

    c.close()
    return {"ok": False, "error": "invalid_action", "task_id": task_id, "action": action}



@app.get("/api/tmp_exec_html")
def tmp_exec_html(limit: int = Query(30, ge=1, le=100)):
    root = Path("/Users/doyopc/AI/openclaw-factory-daemon/public_preview/tmp_exec_lp")
    items = []
    if root.exists():
        for f in sorted(root.glob("*.html"), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
            items.append({
                "name": f.name,
                "path": str(f),
                "mtime": int(f.stat().st_mtime),
                "size": f.stat().st_size
            })
    return {"count": len(items), "items": items}


@app.get("/api/tmp_exec_html_file")
def tmp_exec_html_file(name: str):
    from fastapi.responses import FileResponse
    path = Path("/Users/doyopc/AI/openclaw-factory-daemon/public_preview/tmp_exec_lp") / name
    if path.exists():
        return FileResponse(path)
    return {"error":"not found"}
