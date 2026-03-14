import os
import sqlite3
import time

DB_PATH = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def db():
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    return con

def calc_weight(sample_count, success_count, avg_impact, avg_result):
    sr = (success_count / sample_count) if sample_count else 0.0
    return round(sr * 60 + avg_impact * 8 + avg_result * 4 + min(sample_count, 20), 3)

def upsert_pattern(con, pattern_type, pattern_key, sample_count, success_count, avg_impact, avg_result):
    weight = calc_weight(sample_count, success_count, avg_impact, avg_result)
    con.execute("""
        insert into learning_patterns(
          pattern_type, pattern_key, sample_count, success_count,
          avg_impact_score, avg_result_score, weight, updated_at
        ) values(?,?,?,?,?,?,?,datetime('now'))
        on conflict(pattern_type, pattern_key) do update set
          sample_count=excluded.sample_count,
          success_count=excluded.success_count,
          avg_impact_score=excluded.avg_impact_score,
          avg_result_score=excluded.avg_result_score,
          weight=excluded.weight,
          updated_at=datetime('now')
    """, (
        pattern_type, pattern_key, sample_count, success_count,
        avg_impact, avg_result, weight
    ))

def rebuild_patterns(con):
    con.execute("delete from learning_patterns")

    queries = {
        "source_ai": """
            select
              coalesce(source_ai,'') as k,
              count(*) as n,
              sum(case when coalesce(success_flag,0)=1 then 1 else 0 end) as s,
              avg(coalesce(impact_score,0)) as ai,
              avg(coalesce(result_score,0)) as ar
            from learning_results
            group by coalesce(source_ai,'')
            having trim(coalesce(source_ai,'')) <> ''
        """,
        "target_system": """
            select
              coalesce(target_system,'') as k,
              count(*) as n,
              sum(case when coalesce(success_flag,0)=1 then 1 else 0 end) as s,
              avg(coalesce(impact_score,0)) as ai,
              avg(coalesce(result_score,0)) as ar
            from learning_results
            group by coalesce(target_system,'')
            having trim(coalesce(target_system,'')) <> ''
        """,
        "improvement_type": """
            select
              coalesce(improvement_type,'') as k,
              count(*) as n,
              sum(case when coalesce(success_flag,0)=1 then 1 else 0 end) as s,
              avg(coalesce(impact_score,0)) as ai,
              avg(coalesce(result_score,0)) as ar
            from learning_results
            group by coalesce(improvement_type,'')
            having trim(coalesce(improvement_type,'')) <> ''
        """,
        "source_target": """
            select
              coalesce(source_ai,'') || '|' || coalesce(target_system,'') as k,
              count(*) as n,
              sum(case when coalesce(success_flag,0)=1 then 1 else 0 end) as s,
              avg(coalesce(impact_score,0)) as ai,
              avg(coalesce(result_score,0)) as ar
            from learning_results
            group by coalesce(source_ai,''), coalesce(target_system,'')
            having trim(coalesce(source_ai,'')) <> '' or trim(coalesce(target_system,'')) <> ''
        """,
        "target_improvement": """
            select
              coalesce(target_system,'') || '|' || coalesce(improvement_type,'') as k,
              count(*) as n,
              sum(case when coalesce(success_flag,0)=1 then 1 else 0 end) as s,
              avg(coalesce(impact_score,0)) as ai,
              avg(coalesce(result_score,0)) as ar
            from learning_results
            group by coalesce(target_system,''), coalesce(improvement_type,'')
            having trim(coalesce(target_system,'')) <> '' or trim(coalesce(improvement_type,'')) <> ''
        """
    }

    inserted = 0
    for pattern_type, sql in queries.items():
        rows = con.execute(sql).fetchall()
        for r in rows:
            upsert_pattern(
                con,
                pattern_type,
                r["k"],
                int(r["n"] or 0),
                int(r["s"] or 0),
                float(r["ai"] or 0),
                float(r["ar"] or 0),
            )
            inserted += 1
    con.commit()
    return inserted

def run_once():
    con = db()
    try:
        n = rebuild_patterns(con)
        top = con.execute("""
            select pattern_type, pattern_key, sample_count, success_count, round(weight,2)
            from learning_patterns
            order by weight desc, sample_count desc, id desc
            limit 15
        """).fetchall()
        print(f"pattern_extractor_updated={n}", flush=True)
        for r in top:
            print(tuple(r), flush=True)
    finally:
        con.close()

if __name__ == "__main__":
    while True:
        run_once()
        time.sleep(300)
