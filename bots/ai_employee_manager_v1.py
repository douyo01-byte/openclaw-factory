import os
import sqlite3
from datetime import datetime

DB=os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def table_cols(conn, table):
    try:
        return {r[1] for r in conn.execute(f"pragma table_info({table})").fetchall()}
    except Exception:
        return set()

def main():
    conn=sqlite3.connect(DB, timeout=30)
    conn.execute("pragma busy_timeout=30000")
    cols=table_cols(conn, "dev_proposals")
    if not {"id","status","dev_stage","pr_status"}.issubset(cols):
        print("[ai_employee_manager] dev_proposals schema not ready")
        return
    if "source_ai" not in cols:
        print("[ai_employee_manager] source_ai missing; skip")
        return

    conn.execute("""
    create table if not exists ai_employee_scores(
      source_ai text primary key,
      total_count integer not null default 0,
      merged_count integer not null default 0,
      updated_at text not null
    )
    """)

    rows=conn.execute("""
    select
      source_ai,
      count(*) as total_count,
      sum(case when coalesce(status,'')='merged'
                and coalesce(dev_stage,'')='merged'
                and coalesce(pr_status,'')='merged'
               then 1 else 0 end) as merged_count
    from dev_proposals
    where coalesce(source_ai,'')<>''
    group by source_ai
    order by merged_count desc, total_count desc, source_ai asc
    """).fetchall()

    now=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("delete from ai_employee_scores")
    conn.executemany("""
    insert into ai_employee_scores(source_ai,total_count,merged_count,updated_at)
    values(?,?,?,?)
    """, [(r[0], int(r[1] or 0), int(r[2] or 0), now) for r in rows])
    conn.commit()
    conn.close()
    print(f"[ai_employee_manager] updated {len(rows)} employees")

if __name__ == "__main__":
    main()
