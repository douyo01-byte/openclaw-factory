#!/usr/bin/env python3
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from conversation_intent_router_v1 import classify
from conversation_context_resolver_v1 import resolve_context
from task_decomposer_v1 import decompose

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))

def now_expr() -> str:
    return "datetime('now')"

def connect():
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    return con

def ensure_cols(c):
    cols = {r["name"] for r in c.execute("pragma table_info(inbox_commands)").fetchall()}
    adds = {
        "router_status": "alter table inbox_commands add column router_status text default ''",
        "router_target": "alter table inbox_commands add column router_target text default ''",
        "router_mode": "alter table inbox_commands add column router_mode text default ''",
        "conversation_job_id": "alter table inbox_commands add column conversation_job_id integer default 0",
    }
    for k, sql in adds.items():
        if k not in cols:
            c.execute(sql)

def fetch_rows(c, limit=20):
    return c.execute(
        """
        select id, chat_id, message_id, text, coalesce(status,'') as status,
               coalesce(router_status,'') as router_status,
               coalesce(conversation_job_id,0) as conversation_job_id
        from inbox_commands
        where coalesce(status,'')='new'
          and coalesce(conversation_job_id,0)=0
        order by id asc
        limit ?
        """,
        (limit,),
    ).fetchall()

def create_job(c, row):
    text = row["text"] or ""
    intent = classify(text)
    context = resolve_context(text)
    plan = decompose(intent["domain"], text, context)

    c.execute(
        """
        insert into conversation_jobs(
          source_chat_id, source_message_id, domain, request_text, target_object,
          current_phase, status, assigned_ai, parent_job_id, created_at, updated_at
        ) values(?,?,?,?,?,'planned','new','Kaikun04',null,datetime('now'),datetime('now'))
        """,
        (
            row["chat_id"],
            row["message_id"],
            plan["domain"],
            plan["request_text"],
            context.get("target_object",""),
        )
    )
    job_id = c.lastrowid

    for s in plan["steps"]:
        c.execute(
            """
            insert into conversation_job_steps(
              job_id, step_type, step_order, status, input_json, output_json,
              created_at, updated_at
            ) values(?,?,?,?,?,?,datetime('now'),datetime('now'))
            """,
            (
                job_id,
                s["step_type"],
                s["step_order"],
                "new",
                json.dumps({
                    "context": context,
                    "intent": intent,
                    "source_inbox_command_id": row["id"],
                }, ensure_ascii=False),
                None,
            )
        )

    c.execute(
        """
        update inbox_commands
        set router_status='conversation_job_created',
            router_target='telegram_os',
            router_mode='conversation',
            conversation_job_id=?,
            applied_at=datetime('now')
        where id=?
        """,
        (job_id, row["id"])
    )
    return job_id, plan["domain"]

def run_once():
    con = connect()
    cur = con.cursor()
    ensure_cols(cur)
    rows = fetch_rows(cur, 20)
    made = 0
    for row in rows:
        try:
            job_id, domain = create_job(cur, row)
            print(f"created inbox_id={row['id']} job_id={job_id} domain={domain}", flush=True)
            made += 1
        except Exception as e:
            cur.execute(
                """
                update inbox_commands
                set router_status='conversation_job_error',
                    router_target='telegram_os',
                    router_mode='conversation',
                    error=?,
                    applied_at=datetime('now')
                where id=?
                """,
                (str(e)[:1000], row["id"])
            )
            print(f"error inbox_id={row['id']} err={e}", flush=True)
    con.commit()
    con.close()
    print(f"done made={made}", flush=True)

if __name__ == "__main__":
    run_once()
