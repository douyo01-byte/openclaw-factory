import os
import sqlite3

DB = os.environ.get("DB_PATH", "data/openclaw.db")

def matched_band(v):
    try:
        n = int(v or 0)
    except Exception:
        n = 0
    if n <= 0:
        return "0"
    if n <= 3:
        return "1_3"
    if n <= 7:
        return "4_7"
    if n <= 12:
        return "8_12"
    return "13_plus"

def main():
    conn = sqlite3.connect(DB)
    conn.execute("""
    create table if not exists decider_feedback_metrics (
      source_ai text not null,
      decision text not null,
      matched_band text not null,
      sample_count integer not null,
      avg_source_bias real not null,
      avg_cluster_bias real not null,
      updated_at text default (datetime('now')),
      primary key (source_ai, decision, matched_band)
    )
    """)

    rows = conn.execute("""
    select
      lower(coalesce(dp.source_ai,'')) as source_ai,
      coalesce(json_extract(de.payload,'$.decision'),'') as decision,
      coalesce(json_extract(de.payload,'$.matched_count'),0) as matched_count,
      coalesce(json_extract(de.payload,'$.source_bias'),0) as source_bias,
      coalesce(json_extract(de.payload,'$.cluster_bias'),0) as cluster_bias
    from dev_events de
    join dev_proposals dp on dp.id = de.proposal_id
    where de.event_type='decider_patterns_applied'
    order by de.id desc
    limit 5000
    """).fetchall()

    agg = {}
    for source_ai, decision, matched_count, source_bias, cluster_bias in rows:
        s = str(source_ai or "").strip().lower()
        d = str(decision or "").strip()
        mb = matched_band(matched_count)
        key = (s, d, mb)
        if key not in agg:
            agg[key] = [0, 0.0, 0.0]
        agg[key][0] += 1
        agg[key][1] += float(source_bias or 0.0)
        agg[key][2] += float(cluster_bias or 0.0)

    out = []
    for (source_ai, decision, mb), (cnt, ssum, csum) in agg.items():
        out.append((
            source_ai,
            decision,
            mb,
            cnt,
            0.0 if cnt == 0 else ssum / cnt,
            0.0 if cnt == 0 else csum / cnt,
        ))

    conn.execute("delete from decider_feedback_metrics")
    conn.executemany("""
    insert into decider_feedback_metrics(
      source_ai, decision, matched_band,
      sample_count, avg_source_bias, avg_cluster_bias
    ) values(?,?,?,?,?,?)
    """, out)
    conn.commit()
    conn.close()
    print(f"decider_feedback_done={len(out)}", flush=True)

if __name__ == "__main__":
    main()
