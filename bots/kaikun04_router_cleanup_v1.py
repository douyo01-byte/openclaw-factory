from __future__ import annotations
import os
import sqlite3

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def run_once():
    conn = sqlite3.connect(DB, timeout=30, isolation_level=None)
    try:
        conn.execute("pragma busy_timeout=30000")
        conn.execute("""
            update router_tasks
            set status='timeout',
                finished_at=datetime('now'),
                updated_at=datetime('now'),
                result_text=coalesce(result_text,'') || ' | timeout_auto_closed'
            where coalesce(target_bot,'')='kaikun04'
              and coalesce(status,'') in ('new','started')
              and datetime(coalesce(updated_at, created_at, datetime('now'))) <= datetime('now','-30 minutes')
        """)
        conn.execute("""
            update router_tasks
            set status='orphan',
                finished_at=datetime('now'),
                updated_at=datetime('now'),
                result_text=coalesce(result_text,'') || ' | orphan_auto_closed'
            where coalesce(status,'') in ('new','started')
              and source_command_id is not null
              and not exists (
                select 1 from inbox_commands i where i.id = router_tasks.source_command_id
              )
        """)
        print("[kaikun04_router_cleanup_v1] ok", flush=True)
    finally:
        conn.close()

def main():
    try:
        run_once()
    except sqlite3.OperationalError as e:
        print(f"[kaikun04_router_cleanup_v1] lock_or_db_err={e!r}", flush=True)
    except Exception as e:
        print(f"[kaikun04_router_cleanup_v1] err={e!r}", flush=True)

if __name__ == "__main__":
    main()
