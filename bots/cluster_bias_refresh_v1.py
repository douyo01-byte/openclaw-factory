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

        base = (avg_result_score * 0.55) + (avg_impact_score * 0.45)

        if success_count <= 1:
            base *= 0.18
        elif success_count <= 2:
            base *= 0.32
        elif success_count <= 4:
            base *= 0.52
        elif success_count <= 7:
            base *= 0.72
        else:
            base *= 0.90

        base *= math.log(success_count + 1, 2) * 0.38

        if source_ai == "":
            base = 0.0

        base = clamp(base, -0.75, 0.75)

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

    top5 = sorted(out, key=lambda x: x[6], reverse=True)[:5]
    print(f"cluster_bias_done={len(out)}", flush=True)
    print("cluster_bias_top5=", top5, flush=True)

if __name__ == "__main__":
    main()
