from __future__ import annotations
import os
import sqlite3
import time
from pathlib import Path
from bots.active_bot_policy_v1 import classify_text

DB = os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or "data/openclaw.db"

def connect():
    conn = sqlite3.connect(DB, timeout=20)
    conn.execute("pragma journal_mode=WAL;")
    conn.execute("pragma busy_timeout=20000;")
    return conn

def ensure_column(conn: sqlite3.Connection):
    cols = [r[1] for r in conn.execute("pragma table_info(dev_proposals)").fetchall()]
    if "target_policy" not in cols:
        conn.execute("alter table dev_proposals add column target_policy text default ''")

def classify_all(conn: sqlite3.Connection):
    rows = conn.execute("""
        select id, title, description, coalesce(target_system,''), coalesce(improvement_type,'')
        from dev_proposals
        where coalesce(target_policy,'')=''
    """).fetchall()
    updates = []
    for pid, title, desc, target_system, improvement_type in rows:
        text = " | ".join([
            title or "",
            desc or "",
            target_system or "",
            improvement_type or ""
        ])
        pol = classify_text(text)
        if pol:
            updates.append((pol, pid))
    if updates:
        conn.executemany(
            "update dev_proposals set target_policy=? where id=?",
            updates
        )
    return len(updates)

def block_archived(conn: sqlite3.Connection):
    rows = conn.execute("""
        select id
        from dev_proposals
        where coalesce(target_policy,'')='archived_or_parked'
          and coalesce(status,'') not in ('merged','closed','rejected')
          and (
            coalesce(dev_stage,'') in ('', 'execute_now', 'pr_open', 'approved', 'ready')
            or coalesce(project_decision,'') in ('execute_now','approved')
            or coalesce(guard_status,'')=''
          )
    """).fetchall()
    pids = [r[0] for r in rows]
    if not pids:
        return 0
    conn.executemany("""
        update dev_proposals
        set
          guard_status='blocked_target_policy',
          guard_reason='archived_or_parked target blocked by policy',
          decision_note=trim(coalesce(decision_note,'') || ' | blocked by target policy'),
          dev_stage=case
            when coalesce(dev_stage,'')='merged' then dev_stage
            else 'blocked_target_policy'
          end,
          project_decision=case
            when coalesce(project_decision,'')='execute_now' then 'blocked_target_policy'
            else coalesce(project_decision,'')
          end
        where id=?
    """, [(pid,) for pid in pids])
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    for pid in pids:
        try:
            conn.execute("""
                insert into dev_events(proposal_id,event_type,payload,created_at)
                values(?,?,?,?)
            """, (pid, "target_policy_blocked", '{"reason":"archived_or_parked"}', now))
        except Exception:
            pass
    return len(pids)

def main():
    Path("logs").mkdir(parents=True, exist_ok=True)
    conn = connect()
    try:
        ensure_column(conn)
        n1 = classify_all(conn)
        n2 = block_archived(conn)
        conn.commit()
        print(f"[target_policy_guard] classified={n1} blocked={n2}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
