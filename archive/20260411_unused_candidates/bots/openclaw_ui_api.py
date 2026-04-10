from typing import Optional
from pathlib import Path
from fastapi import FastAPI, Query
from pydantic import BaseModel
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from bots.openclaw_db_adapter import OpenClawDBAdapter
import os

DB_PATH = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

app = FastAPI(title="OpenClaw UI API")

def adapter() -> OpenClawDBAdapter:
    return OpenClawDBAdapter(DB_PATH)

@app.get("/")
def root():
    html = open("ui/index.html", encoding="utf-8").read()
    return Response(content=html, media_type="text/html")

app.mount("/ui", StaticFiles(directory="ui"), name="ui")

@app.get("/health")
def health():
    return {"ok": True, "db_path": DB_PATH}


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
    a = adapter()
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
