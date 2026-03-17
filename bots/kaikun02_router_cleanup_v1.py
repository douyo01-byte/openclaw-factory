import os
import sqlite3
from datetime import datetime, timedelta

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def main():
    conn = sqlite3.connect(DB, timeout=30)
    conn.execute("pragma busy_timeout=30000")
    try:
        conn.execute("""
            update router_tasks
            set
              status='done',
              finished_at=datetime('now'),
              updated_at=datetime('now'),
              result_text=coalesce(result_text,'') || ' | auto_closed_after_route_upgrade'
            where coalesce(target_bot,'')='kaikun02'
              and coalesce(status,'') in ('new','started')
              and datetime(coalesce(updated_at, created_at, datetime('now'))) <= datetime('now','-30 minutes')
              and (
                lower(coalesce(task_text,'')) like '%ボトルネック%'
                or lower(coalesce(task_text,'')) like '%watchpoint%'
                or lower(coalesce(task_text,'')) like '%監視ポイント%'
                or lower(coalesce(task_text,'')) like '%runtime%'
                or lower(coalesce(task_text,'')) like '%reserve%'
                or lower(coalesce(task_text,'')) like '%社員ランキング%'
              )
        """)
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
