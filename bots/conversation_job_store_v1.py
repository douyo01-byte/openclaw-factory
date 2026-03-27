#!/usr/bin/env python3
import json
import os
import sqlite3
import sys

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))

def connect():
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    return con

def create_job(payload: dict) -> dict:
    context = payload.get("context", {})
    steps = payload.get("steps", [])
    con = connect()
    cur = con.cursor()
    cur.execute(
        """
        insert into conversation_jobs(
          source_chat_id, source_message_id, domain, request_text, target_object,
          current_phase, status, assigned_ai, parent_job_id
        ) values(?,?,?,?,?,?,?,?,?)
        """,
        (
            payload.get("source_chat_id"),
            payload.get("source_message_id"),
            payload["domain"],
            payload["request_text"],
            context.get("target_object"),
            "planned",
            "new",
            payload.get("assigned_ai"),
            payload.get("parent_job_id"),
        )
    )
    job_id = cur.lastrowid
    for s in steps:
        cur.execute(
            """
            insert into conversation_job_steps(
              job_id, step_type, step_order, status, input_json, output_json
            ) values(?,?,?,?,?,?)
            """,
            (
                job_id,
                s["step_type"],
                s["step_order"],
                "new",
                json.dumps({"context": context}, ensure_ascii=False),
                None,
            )
        )
    con.commit()
    con.close()
    return {"job_id": job_id, "step_count": len(steps)}

def main() -> None:
    payload = json.loads(sys.stdin.read())
    print(json.dumps(create_job(payload), ensure_ascii=False))

if __name__ == "__main__":
    main()
