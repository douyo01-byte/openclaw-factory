import os
import sqlite3
import time

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    return c

def build_summary(row):
    bits = []
    for k, label in [
        ("source_ai", "source_ai"),
        ("target_system", "target"),
        ("improvement_type", "type"),
        ("impact_level", "impact"),
        ("result_type", "result"),
    ]:
        v = str(row[k] or "").strip()
        if v:
            bits.append(f"{label}={v}")
    return " / ".join(bits) if bits else "merged_result"

def run_once():
    c = conn()
    try:
        rows = c.execute("""
            select
              dp.id as proposal_id,
              coalesce(dp.title,'') as title,
              coalesce(dp.source_ai,'') as source_ai,
              coalesce(dp.target_system,'') as target_system,
              coalesce(dp.improvement_type,'') as improvement_type,
              coalesce(dp.impact_score,0) as impact_score,
              coalesce(dp.impact_level,'') as impact_level,
              coalesce(dp.impact_reason,'') as impact_reason,
              coalesce(dp.result_score,0) as result_score,
              coalesce(dp.result_type,'') as result_type,
              coalesce(dp.result_note,'') as result_note,
              coalesce(dp.executed_at,'') as merged_at
            from dev_proposals dp
            where coalesce(dp.dev_stage,'')='merged'
              and not exists (
                select 1
                from learning_results lr
                where lr.proposal_id = dp.id
              )
            order by dp.id asc
            limit 100
        """).fetchall()

        n = 0
        for r in rows:
            c.execute("""
                insert into learning_results(
                  proposal_id,
                  title,
                  source_ai,
                  target_system,
                  improvement_type,
                  impact_score,
                  impact_level,
                  impact_reason,
                  result_score,
                  result_type,
                  result_note,
                  success_flag,
                  learning_summary,
                  merged_at
                ) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                int(r["proposal_id"]),
                str(r["title"] or ""),
                str(r["source_ai"] or ""),
                str(r["target_system"] or ""),
                str(r["improvement_type"] or ""),
                float(r["impact_score"] or 0),
                str(r["impact_level"] or ""),
                str(r["impact_reason"] or ""),
                float(r["result_score"] or 0),
                str(r["result_type"] or ""),
                str(r["result_note"] or ""),
                1,
                build_summary(r),
                str(r["merged_at"] or ""),
            ))
            n += 1

        c.commit()
        print(f"learning_result_writer_inserted={n}", flush=True)
    finally:
        c.close()

if __name__ == "__main__":
    while True:
        run_once()
        time.sleep(120)
