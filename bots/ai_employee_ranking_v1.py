import os
import sqlite3
from datetime import datetime, UTC

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def main():
    conn = sqlite3.connect(DB, timeout=30)
    conn.execute("pragma busy_timeout=30000")

    conn.execute("""
    create table if not exists ai_employee_rankings(
      rank_no integer not null,
      source_ai text primary key,
      total_count integer not null default 0,
      merged_count integer not null default 0,
      merge_rate real not null default 0,
      score real not null default 0,
      updated_at text not null
    )
    """)

    rows = conn.execute("""
    select
      source_ai,
      total_count,
      merged_count
    from ai_employee_scores
    where coalesce(source_ai,'')<>''
    order by merged_count desc, total_count desc, source_ai asc
    """).fetchall()

    ranked = []
    for source_ai, total_count, merged_count in rows:
        total_count = int(total_count or 0)
        merged_count = int(merged_count or 0)
        merge_rate = (merged_count / total_count) if total_count > 0 else 0.0
        score = round(merged_count * 10.0 + merge_rate * 100.0 + min(total_count, 200) * 0.2, 4)
        ranked.append((source_ai, total_count, merged_count, merge_rate, score))

    ranked.sort(key=lambda x: (-x[4], -x[2], -x[1], x[0]))

    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("delete from ai_employee_rankings")
    conn.executemany("""
    insert into ai_employee_rankings(
      rank_no, source_ai, total_count, merged_count, merge_rate, score, updated_at
    )
    values(?,?,?,?,?,?,?)
    """, [
        (i + 1, r[0], r[1], r[2], r[3], r[4], now)
        for i, r in enumerate(ranked)
    ])

    conn.commit()
    conn.close()
    print(f"[ai_employee_ranking] ranked {len(ranked)} employees", flush=True)

if __name__ == "__main__":
    main()
