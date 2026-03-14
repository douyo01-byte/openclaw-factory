import os
import sqlite3
import time

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    return c

def run_once():
    c = conn()
    try:
        rows = c.execute("""
            select
              pattern_type,
              pattern_key,
              coalesce(weight,0) as weight,
              coalesce(sample_count,0) as sample_count
            from learning_patterns
            where coalesce(sample_count,0) >= 3
            order by weight desc, sample_count desc, id desc
            limit 100
        """).fetchall()

        c.execute("delete from supply_bias")

        n = 0
        for r in rows:
            ptype = str(r["pattern_type"] or "").strip()
            pkey = str(r["pattern_key"] or "").strip()
            weight = float(r["weight"] or 0)
            sample_count = int(r["sample_count"] or 0)

            if not ptype or not pkey:
                continue

            c.execute("""
                insert into supply_bias(
                  bias_type,
                  bias_key,
                  weight,
                  source_pattern_count,
                  updated_at
                ) values(?,?,?,?,datetime('now'))
            """, (
                ptype,
                pkey,
                weight,
                sample_count
            ))
            n += 1

        c.commit()
        print(f"supply_bias_updated={n}", flush=True)
    finally:
        c.close()

if __name__ == "__main__":
    while True:
        run_once()
        time.sleep(180)
