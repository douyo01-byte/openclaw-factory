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
    src = (row["source_ai"] or "").strip()
    tgt = (row["target_system"] or "").strip()
    imp = (row["improvement_type"] or "").strip()
    lvl = (row["impact_level"] or "").strip()
    rtype = (row["result_type"] or "").strip()
    if src:
        bits.append(f"source_ai={src}")
    if tgt:
        bits.append(f"target={tgt}")
    if imp:
        bits.append(f"type={imp}")
    if lvl:
        bits.append(f"impact={lvl}")
    if rtype:
        bits.append(f"result={rtype}")
    return " / ".join(bits) if bits else "merged_result"

def run_once():
    c = conn()
    try:
        rows = c.execute("""
            select
              id as proposal_id,
              coalesce(title,'') as title,
              coalesce(source_ai,'') as source_ai,
              coalesce(target_system,'') as target_system,
              coalesce(improvement_type,'') as improvement_type,
              coalesce(impact_score,0) as impact_score,
              coalesce(impact_level,'') as impact_level,
              coalesce(impact_reason,'') as impact_reason,
              coalesce(result_score,0) as result_score,
              coalesce(result_type,'') as result_type,
              coalesce(result_note,'') as result_note,
              coalesce(executed_at,'') as executed_at,
              coalesce(created_at,'') as created_at
            from dev_proposals
            where coalesce(dev_stage,'')='merged'
              and not exists (
                select 1 from learning_results lr
                where lr.proposal_id = dev_proposals.id
              )
            order by id asc
            limit 100
        """).fetchall()

        n = 0
        for r in rows:
            success_flag = 1
            merged_at = (r["executed_at"] or r["created_at"] or "").strip()
            summary = build_summary(r)
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
                r["proposal_id"],
                r["title"],
                r["source_ai"],
                r["target_system"],
                r["improvement_type"],
                float(r["impact_score"] or 0),
                r["impact_level"],
                r["impact_reason"],
                float(r["result_score"] or 0),
                r["result_type"],
                r["result_note"],
                success_flag,
                summary,
                merged_at
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
