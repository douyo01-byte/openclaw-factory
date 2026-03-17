from __future__ import annotations
import os
import sqlite3

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def main():
    conn = sqlite3.connect(DB, timeout=30)
    try:
        conn.execute("pragma busy_timeout=30000")
        conn.execute("""
            update router_tasks
            set status='done',
                finished_at=datetime('now'),
                updated_at=datetime('now'),
                result_text=coalesce(result_text,'') || ' | auto_closed_after_stale_relay'
            where coalesce(target_bot,'')='kaikun04'
              and coalesce(status,'') in ('new','started')
              and datetime(coalesce(updated_at, created_at, datetime('now'))) <= datetime('now','-30 minutes')
        """)
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
