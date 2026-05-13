#!/usr/bin/env python3
import os
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get(
    "DB_PATH",
    str(Path.home() / "AI/openclaw-factory/data/openclaw.db")
)

def con():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

def main():
    db = con()

    rows = db.execute("""
        select
          id,
          artifact_path,
          status
        from revenue_experiments
        where artifact_path != ''
    """).fetchall()

    for r in rows:
        score = 0

        if "lp_" in r["artifact_path"]:
            score += 10

        db.execute("""
            insert into revenue_metrics
            (
              experiment_id,
              metric_name,
              metric_value,
              source,
              captured_at
            )
            values
            (?, 'artifact_score', ?, 'local_judge', datetime('now'))
        """, (
            r["id"],
            score
        ))

        if score >= 10:
            db.execute("""
                update revenue_experiments
                set status='winner_candidate',
                    updated_at=datetime('now')
                where id=?
            """, (r["id"],))

    db.commit()

    print("winner judged")

if __name__ == "__main__":
    main()
