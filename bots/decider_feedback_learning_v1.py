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
      source_ai text,
      decision text,
      matched_band text,
      sample_count integer,
      avg_source_bias real,
      avg_cluster_bias real,
      updated_at text default (datetime('now')),
      primary key (source_ai, decision, matched_band)
    )
    """)
    rows = conn.execute("""
    with latest as (
      select
        proposal_id,
        max(id) as max_id
      from dev_events
      where event_type='decider_patterns_applied'
      group by proposal_id
    )
    select
      lower(coalesce(dp.source_ai,'')) as source_ai,
      lower(coalesce(json_extract(de.payload,'$.decision'),'')) as decision,
      json_extract(de.payload,'$.matched_count') as matched_count,
      coalesce(json_extract(de.payload,'$.source_bias'),0) as source_bias,
      coalesce(json_extract(de.payload,'$.cluster_bias'),0) as cluster_bias
    from latest l
    join dev_events de
      on de.id = l.max_id
    left join dev_proposals dp
      on dp.id = de.proposal_id
    where de.event_type='decider_patterns_applied'
    """).fetchall()

    agg = {}
    old_payload_count = 0

    def band(v):
        if v is None:
            return "old_payload"
        try:
            n = int(v)
        except Exception:
            return "old_payload"
        if n <= 0:
            return "old_payload"
        if n <= 3:
            return "1_3"
        if n <= 7:
            return "4_7"
        if n <= 12:
            return "8_12"
        return "13_plus"

    for source_ai, decision, matched_count, source_bias, cluster_bias in rows:
        mb = band(matched_count)
        if mb == "old_payload":
            old_payload_count += 1
            continue
        key = (str(source_ai or "").strip(), str(decision or "").strip(), mb)
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
    print(f"decider_feedback_old_payload_skipped={old_payload_count}", flush=True)
if __name__ == "__main__":
    main()
