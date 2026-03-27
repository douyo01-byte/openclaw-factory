from __future__ import annotations
import os
import re
import sqlite3
import time

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = float(os.environ.get("KAIKUN04_EXEC_BRIDGE_SLEEP", "3"))
EXEC_RE = re.compile(r"(?ms)^\[EXEC\]\s*script=([A-Za-z0-9_.-]+)\s*$")

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
        "exec_bridge_status": "alter table router_tasks add column exec_bridge_status text default ''",
        "exec_bridge_reason": "alter table router_tasks add column exec_bridge_reason text default ''",
        "exec_child_task_id": "alter table router_tasks add column exec_child_task_id integer default 0",
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
    c.execute("create index if not exists idx_self_improvement_parent on self_improvement_log(parent_task_id)")

def fetch_rows(c):
    return c.execute("""
        select
          id,
          source_command_id,
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

def log_queued(c, parent_task_id: int, child_task_id: int, source_command_id: int, script: str, parent_reply_text: str):
    c.execute("""
        insert into self_improvement_log(
          parent_task_id, child_task_id, source_command_id, kind,
          problem, fix, result, reusable_pattern,
          status, parent_reply_head, child_result_head,
          created_at, applied_at, updated_at
        ) values(
          ?, ?, ?, 'exec_bridge',
          'repetitive terminal work detected',
          ?, 'queued_child_task', 'allowlisted exec delegation',
          'queued', ?, '',
          datetime('now'), '', datetime('now')
        )
    """, (
        parent_task_id,
        child_task_id,
        source_command_id,
        f"script={script}",
        head(parent_reply_text),
    ))

def log_skipped(c, parent_task_id: int, source_command_id: int, reason: str, parent_reply_text: str):
    c.execute("""
        insert into self_improvement_log(
          parent_task_id, child_task_id, source_command_id, kind,
          problem, fix, result, reusable_pattern,
          status, parent_reply_head, child_result_head,
          created_at, applied_at, updated_at
        ) values(
          ?, null, ?, 'exec_bridge',
          'no reusable exec delegation',
          ?, 'bridge_skipped', '',
          'skipped', ?, '',
          datetime('now'), datetime('now'), datetime('now')
        )
    """, (
        parent_task_id,
        source_command_id,
        reason,
        head(parent_reply_text),
    ))

def tick():
    done = 0
    skipped = 0
    c = conn()
    try:
        ensure_schema(c)
        rows = fetch_rows(c)
        for r in rows:
            parent_task_id = int(r["id"])
            source_command_id = int(r["source_command_id"] or 0)
            reply_text = r["reply_text"] or ""
            script = extract_script(reply_text)
            if not script:
                mark_skipped(c, parent_task_id, "no_exec_block")
                log_skipped(c, parent_task_id, source_command_id, "no_exec_block", reply_text)
                skipped += 1
                continue
            child_task_id = insert_child(c, source_command_id, script)
            mark_queued(c, parent_task_id, child_task_id)
            log_queued(c, parent_task_id, child_task_id, source_command_id, script, reply_text)
            done += 1
            print(f"[kaikun04_exec_bridge_v1] queued parent={parent_task_id} child={child_task_id} script={script}", flush=True)
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
