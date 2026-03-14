import os
import re
import sqlite3
import time

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    return c

def norm(v):
    return str(v or "").strip().lower()

def title_bucket(title: str) -> str:
    t = norm(title)
    if not t:
        return "misc"
    if "health" in t:
        return "health"
    if "db " in f"{t} " or "database" in t:
        return "db"
    if "watcher" in t:
        return "watcher"
    if "log" in t:
        return "log"
    if "merge" in t:
        return "merge"
    if "executor" in t:
        return "executor"
    if "ceo" in t:
        return "ceo"
    if "proposal" in t:
        return "proposal"
    return re.sub(r'[^a-z0-9_]+', '_', t[:24]).strip('_') or "misc"

def rows_to_patterns(rows):
    buckets = {}

    for r in rows:
        success = int(r["success_flag"] or 0)
        impact = float(r["impact_score"] or 0)
        result = float(r["result_score"] or 0)

        pairs = []

        src = norm(r["source_ai"])
        tgt = norm(r["target_system"])
        imp = norm(r["improvement_type"])
        title = str(r["title"] or "")

        if src:
            pairs.append(("source_ai", src))
        if tgt:
            pairs.append(("target_system", tgt))
        if imp:
            pairs.append(("improvement_type", imp))

        pairs.append(("title_bucket", title_bucket(title)))

        for ptype, pkey in pairs:
            k = (ptype, pkey)
            if k not in buckets:
                buckets[k] = {
                    "sample_count": 0,
                    "success_count": 0,
                    "impact_sum": 0.0,
                    "result_sum": 0.0,
                }
            buckets[k]["sample_count"] += 1
            buckets[k]["success_count"] += success
            buckets[k]["impact_sum"] += impact
            buckets[k]["result_sum"] += result

    out = []
    for (ptype, pkey), v in buckets.items():
        n = v["sample_count"]
        s = v["success_count"]
        avg_impact = v["impact_sum"] / n if n else 0.0
        avg_result = v["result_sum"] / n if n else 0.0
        success_rate = s / n if n else 0.0
        weight = round(success_rate * 60 + avg_impact * 5 + avg_result * 20, 4)
        out.append((ptype, pkey, n, s, avg_impact, avg_result, weight))
    return out

def run_once():
    c = conn()
    try:
        rows = c.execute("""
            select
              title,
              coalesce(source_ai,'') as source_ai,
              coalesce(target_system,'') as target_system,
              coalesce(improvement_type,'') as improvement_type,
              coalesce(impact_score,0) as impact_score,
              coalesce(result_score,0) as result_score,
              coalesce(success_flag,0) as success_flag
            from learning_results
            order by id desc
            limit 1000
        """).fetchall()

        pats = rows_to_patterns(rows)

        c.execute("delete from learning_patterns")
        for p in pats:
            c.execute("""
                insert into learning_patterns(
                  pattern_type,
                  pattern_key,
                  sample_count,
                  success_count,
                  avg_impact_score,
                  avg_result_score,
                  weight,
                  updated_at
                ) values(?,?,?,?,?,?,?,datetime('now'))
            """, p)

        c.commit()
        print(f"pattern_extractor_updated={len(pats)}", flush=True)
    finally:
        c.close()

if __name__ == "__main__":
    while True:
        run_once()
        time.sleep(180)
