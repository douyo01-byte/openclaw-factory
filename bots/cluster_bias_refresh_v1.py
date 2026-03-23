import os
import math
import sqlite3

DB = os.environ.get("DB_PATH", "data/openclaw.db")

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def main():
    conn = sqlite3.connect(DB)
    conn.execute("""
    create table if not exists cluster_bias (
      source_ai text,
      target_system text,
      improvement_type text,
      success_count integer,
      avg_result_score real,
      avg_impact_score real,
      bias_score real,
      updated_at text default (datetime('now')),
      primary key (source_ai, target_system, improvement_type)
    )
    """)

    rows = conn.execute("""
    select
      lower(coalesce(source_ai,'')) as source_ai,
      lower(coalesce(target_system,'')) as target_system,
      lower(coalesce(improvement_type,'')) as improvement_type,
      count(*) as total,
      sum(case when coalesce(success_flag,0)=1 then 1 else 0 end) as success_count,
      avg(coalesce(result_score,0)) as avg_result_score,
      avg(coalesce(impact_score,0)) as avg_impact_score
    from learning_results
    group by lower(coalesce(source_ai,'')),
             lower(coalesce(target_system,'')),
             lower(coalesce(improvement_type,''))
    """).fetchall()

    out = []
    for source_ai, target_system, improvement_type, total, success_count, avg_result_score, avg_impact_score in rows:
        source_ai = str(source_ai or "").strip()
        target_system = str(target_system or "").strip()
        improvement_type = str(improvement_type or "").strip()
        total = int(total or 0)
        success_count = int(success_count or 0)
        avg_result_score = float(avg_result_score or 0.0)
        avg_impact_score = float(avg_impact_score or 0.0)

        base = avg_result_score + avg_impact_score

        if success_count < 3:
            base *= 0.4
        elif success_count < 6:
            base *= 0.7

        base *= math.log(success_count + 1, 2) * 0.55

        if source_ai == "":
            base = 0.0

        base = clamp(base, -1.2, 1.2)

        out.append((
            source_ai,
            target_system,
            improvement_type,
            success_count,
            avg_result_score,
            avg_impact_score,
            base,
        ))

    conn.execute("delete from cluster_bias")
    conn.executemany("""
    insert into cluster_bias(
      source_ai,target_system,improvement_type,
      success_count,avg_result_score,avg_impact_score,bias_score
    ) values(?,?,?,?,?,?,?)
    """, out)
    conn.commit()
    conn.close()
    print(f"cluster_bias_done={len(out)}", flush=True)

if __name__ == "__main__":
    main()
