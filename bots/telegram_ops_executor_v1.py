from __future__ import annotations
import os
import re
import sqlite3
import subprocess
import time
from pathlib import Path

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
ROOT = Path("/Users/doyopc/AI/openclaw-factory-daemon")
OPS_DIR = ROOT / "ops" / "telegram_exec"
SLEEP = float(os.environ.get("TELEGRAM_OPS_EXECUTOR_SLEEP", "3"))
MAX_OUT = int(os.environ.get("TELEGRAM_OPS_EXECUTOR_MAX_OUT", "3500"))
TASK_ID_RE = re.compile(r"\[TASK_ID:\d+\]")
TAG_RE = re.compile(r"^\[(EXEC|FAST|DOC|THINK|TASK|MODE:[^\]]+)\]\s*$", re.MULTILINE)

def head(text: str, n: int = 300) -> str:
    s = (text or "").strip().replace("\r", "\n")
    return s[:n]

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    try:
        c.execute("pragma journal_mode=WAL")
    except Exception:
        pass
    return c

def ensure_cols(c, table: str, adds: dict[str, str]):
    cols = {r["name"] for r in c.execute(f"pragma table_info({table})").fetchall()}
    for k, sql in adds.items():
        if k not in cols:
            c.execute(sql)

def ensure_schema(c):
    ensure_cols(c, "router_tasks", {
        "reply_text": "alter table router_tasks add column reply_text text default ''",
        "sent_message_id": "alter table router_tasks add column sent_message_id text default ''",
        "started_at": "alter table router_tasks add column started_at text default ''",
        "finished_at": "alter table router_tasks add column finished_at text default ''",
        "validation_status": "alter table router_tasks add column validation_status text default ''",
        "validation_reason": "alter table router_tasks add column validation_reason text default ''",
        "retry_count": "alter table router_tasks add column retry_count integer default 0",
    })
    c.execute("""
        create table if not exists self_improvement_log(
          id integer primary key autoincrement,
          parent_task_id integer not null,
          child_task_id integer,
          source_command_id integer,
          kind text not null default 'exec_bridge',
          problem text not null default '',
          fix text not null default '',
          result text not null default '',
          reusable_pattern text not null default '',
          created_at text default (datetime('now'))
        )
    """)
    ensure_cols(c, "self_improvement_log", {
        "status": "alter table self_improvement_log add column status text not null default ''",
        "parent_reply_head": "alter table self_improvement_log add column parent_reply_head text not null default ''",
        "child_result_head": "alter table self_improvement_log add column child_result_head text not null default ''",
        "applied_at": "alter table self_improvement_log add column applied_at text default ''",
        "updated_at": "alter table self_improvement_log add column updated_at text default ''",
    })
    c.execute("create index if not exists idx_self_improvement_child on self_improvement_log(child_task_id)")

def clean_task_text(s: str) -> str:
    s = (s or "").replace("\r", "\n")
    s = TASK_ID_RE.sub("", s)
    s = TAG_RE.sub("", s)
    return s.strip()

def parse_payload(s: str):
    script = ""
    args: list[str] = []
    for raw in clean_task_text(s).splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("script="):
            script = line.split("=", 1)[1].strip()
        elif line.startswith("arg="):
            args.append(line.split("=", 1)[1])
    return script, args

def allowed_script_path(name: str) -> Path:
    if not name or "/" in name or "\\" in name or name.startswith("."):
        raise RuntimeError("invalid_script")
    p = (OPS_DIR / name).resolve()
    if OPS_DIR.resolve() not in p.parents:
        raise RuntimeError("script_outside_allowlist")
    if not p.exists():
        raise RuntimeError("script_not_found")
    if not os.access(p, os.X_OK):
        raise RuntimeError("script_not_executable")
    return p

def run_script(name: str, args: list[str]) -> str:
    p = allowed_script_path(name)
    cmd = [str(p), *args]
    env = os.environ.copy()
    env["DB_PATH"] = DB
    env["OCLAW_DB_PATH"] = DB
    env["FACTORY_DB_PATH"] = DB
    r = subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    out = ""
    if r.stdout:
        out += r.stdout
    if r.stderr:
        if out:
            out += "\n"
        out += r.stderr
    out = out.strip()
    prefix = f"script={name}\nexit={r.returncode}"
    out = prefix if not out else prefix + "\n\n" + out
    if len(out) > MAX_OUT:
        out = out[:MAX_OUT] + "\n\n[truncated]"
    return out

def fetch_rows(c):
    return c.execute("""
        select id, source_command_id, task_text
        from router_tasks
        where coalesce(target_bot,'')='ops_exec'
          and coalesce(status,'')='new'
        order by id asc
        limit 5
    """).fetchall()

def update_self_improvement(c, child_task_id: int, status: str, result: str, applied: bool):
    c.execute("""
        update self_improvement_log
        set status=?,
            result=?,
            child_result_head=?,
            applied_at=case when ? then datetime('now') else coalesce(applied_at,'') end,
            updated_at=datetime('now')
        where child_task_id=?
    """, (status, result, head(result), 1 if applied else 0, child_task_id))

def mark_started(c, task_id: int):
    c.execute("""
        update router_tasks
        set status='started',
            started_at=case when coalesce(started_at,'')='' then datetime('now') else started_at end,
            updated_at=datetime('now')
        where id=?
    """, (task_id,))

def mark_done(c, task_id: int, cmd_id: int, reply: str):
    c.execute("""
        update router_tasks
        set status='done',
            reply_text=?,
            validation_status='ok',
            validation_reason='',
            finished_at=datetime('now'),
            updated_at=datetime('now')
        where id=?
    """, (reply, task_id))
    c.execute("""
        update inbox_commands
        set router_finish_status='applied',
            router_task_id=?,
            updated_at=datetime('now')
        where id=?
    """, (task_id, cmd_id))
    update_self_improvement(c, task_id, "done", "queued_child_task_done", True)

def mark_failed(c, task_id: int, cmd_id: int, reason: str):
    reply = f"[TASK_ID:{task_id}]\n[EXEC RESULT]\nstatus=failed\nreason={reason}"
    c.execute("""
        update router_tasks
        set status='failed',
            reply_text=?,
            validation_status='invalid_output',
            validation_reason=?,
            retry_count=coalesce(retry_count,0)+1,
            finished_at=datetime('now'),
            updated_at=datetime('now')
        where id=?
    """, (reply, reason, task_id))
    c.execute("""
        update inbox_commands
        set router_finish_status='applied',
            router_task_id=?,
            updated_at=datetime('now')
        where id=?
    """, (task_id, cmd_id))
    update_self_improvement(c, task_id, "failed", f"failed:{reason}", False)

def mark_skipped(c, task_id: int, cmd_id: int, reason: str):
    reply = f"[TASK_ID:{task_id}]\n[EXEC RESULT]\nstatus=skipped\nreason={reason}"
    c.execute("""
        update router_tasks
        set status='skipped',
            reply_text=?,
            validation_status='skipped',
            validation_reason=?,
            finished_at=datetime('now'),
            updated_at=datetime('now')
        where id=?
    """, (reply, reason, task_id))
    c.execute("""
        update inbox_commands
        set status='done',
            processed=1,
            router_finish_status='skipped_bad_exec_payload',
            router_task_id=?,
            updated_at=datetime('now')
        where id=?
    """, (task_id, cmd_id))
    update_self_improvement(c, task_id, "skipped", f"skipped:{reason}", False)

def tick():
    done = 0
    with conn() as c:
        ensure_schema(c)
        rows = fetch_rows(c)
        for r in rows:
            task_id = r["id"]
            cmd_id = r["source_command_id"]
            mark_started(c, task_id)
            c.commit()
            try:
                script, args = parse_payload(r["task_text"])
                if not script:
                    mark_skipped(c, task_id, cmd_id, "missing_script")
                    c.commit()
                    print(f"[telegram_ops_executor_v1] skipped task_id={task_id} reason=missing_script", flush=True)
                    continue
                out = run_script(script, args)
                reply = f"[TASK_ID:{task_id}]\n[EXEC RESULT]\n{out}"
                mark_done(c, task_id, cmd_id, reply)
                c.commit()
                done += 1
                print(f"[telegram_ops_executor_v1] done task_id={task_id} script={script}", flush=True)
            except RuntimeError as e:
                if str(e) in {"invalid_script", "script_outside_allowlist", "script_not_found", "script_not_executable"}:
                    mark_skipped(c, task_id, cmd_id, str(e))
                    c.commit()
                    print(f"[telegram_ops_executor_v1] skipped task_id={task_id} reason={e}", flush=True)
                else:
                    mark_failed(c, task_id, cmd_id, f"{type(e).__name__}:{e}")
                    c.commit()
                    print(f"[telegram_ops_executor_v1] failed task_id={task_id} err={e!r}", flush=True)
            except Exception as e:
                mark_failed(c, task_id, cmd_id, f"{type(e).__name__}:{e}")
                c.commit()
                print(f"[telegram_ops_executor_v1] failed task_id={task_id} err={e!r}", flush=True)
    print(f"[telegram_ops_executor_v1] done={done}", flush=True)

def main():
    while True:
        try:
            tick()
        except Exception as e:
            print(f"[telegram_ops_executor_v1] fatal err={e!r}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
