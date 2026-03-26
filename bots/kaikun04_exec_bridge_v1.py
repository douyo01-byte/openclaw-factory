from __future__ import annotations
import os
import re
import sqlite3
import time

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = float(os.environ.get("KAIKUN04_EXEC_BRIDGE_SLEEP", "3"))

EXEC_RE = re.compile(r"(?ms)^\[EXEC\]\s*script=([A-Za-z0-9_.-]+)\s*$")

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    try:
        c.execute("pragma journal_mode=WAL")
    except Exception:
        pass
    return c

def ensure_schema(c):
    cols = {r["name"] for r in c.execute("pragma table_info(router_tasks)").fetchall()}
    adds = {
        "exec_bridge_status": "alter table router_tasks add column exec_bridge_status text default ''",
        "exec_bridge_reason": "alter table router_tasks add column exec_bridge_reason text default ''",
        "exec_child_task_id": "alter table router_tasks add column exec_child_task_id integer default 0",
    }
    for k, sql in adds.items():
        if k not in cols:
            c.execute(sql)
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

def fetch_rows(c):
    return c.execute("""
        select
          id,
          source_command_id,
          mode,
          target_bot,
          coalesce(reply_text,'') as reply_text,
          coalesce(exec_bridge_status,'') as exec_bridge_status
        from router_tasks
        where coalesce(target_bot,'')='kaikun04'
          and coalesce(status,'')='done'
          and coalesce(reply_text,'')<>''
          and coalesce(exec_bridge_status,'')=''
        order by id asc
        limit 20
    """).fetchall()

def extract_script(reply_text: str) -> str:
    m = EXEC_RE.search((reply_text or "").strip())
    return (m.group(1).strip() if m else "")

def insert_child(c, source_command_id: int, script: str) -> int:
    task_text = f"[EXEC]\nscript={script}"
    c.execute("""
        insert into router_tasks(
          source_command_id, mode, target_bot, task_text, status, created_at, updated_at
        ) values(
          ?, 'EXEC', 'ops_exec', ?, 'new', datetime('now'), datetime('now')
        )
    """, (source_command_id, task_text))
    return int(c.execute("select last_insert_rowid()").fetchone()[0])

def mark_queued(c, parent_task_id: int, child_task_id: int):
    c.execute("""
        update router_tasks
        set exec_bridge_status='queued',
            exec_bridge_reason='',
            exec_child_task_id=?,
            updated_at=datetime('now')
        where id=?
    """, (child_task_id, parent_task_id))

def mark_skipped(c, parent_task_id: int, reason: str):
    c.execute("""
        update router_tasks
        set exec_bridge_status='skipped',
            exec_bridge_reason=?,
            updated_at=datetime('now')
        where id=?
    """, (reason, parent_task_id))

def log_bridge(c, parent_task_id: int, child_task_id: int, source_command_id: int, script: str):
    c.execute("""
        insert into self_improvement_log(
          parent_task_id, child_task_id, source_command_id, kind, problem, fix, result, reusable_pattern, created_at
        ) values(
          ?, ?, ?, 'exec_bridge',
          'repetitive terminal work detected',
          ?,
          'queued_child_task',
          'allowlisted exec delegation',
          datetime('now')
        )
    """, (parent_task_id, child_task_id, source_command_id, f"script={script}"))

def tick():
    done = 0
    skipped = 0
    c = conn()
    try:
        ensure_schema(c)
        rows = fetch_rows(c)
        for r in rows:
            script = extract_script(r["reply_text"])
            if not script:
                mark_skipped(c, r["id"], "no_exec_block")
                skipped += 1
                continue
            child_task_id = insert_child(c, int(r["source_command_id"] or 0), script)
            mark_queued(c, r["id"], child_task_id)
            log_bridge(c, r["id"], child_task_id, int(r["source_command_id"] or 0), script)
            done += 1
            print(f"[kaikun04_exec_bridge_v1] queued parent={r['id']} child={child_task_id} script={script}", flush=True)
        c.commit()
        print(f"[kaikun04_exec_bridge_v1] done={done} skipped={skipped}", flush=True)
    finally:
        c.close()

def main():
    while True:
        try:
            tick()
        except Exception as e:
            print(f"[kaikun04_exec_bridge_v1] fatal err={e!r}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
