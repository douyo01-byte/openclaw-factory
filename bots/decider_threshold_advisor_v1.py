import os
import sqlite3

DB = os.environ.get("DB_PATH", "data/openclaw.db")

def main():
    conn = sqlite3.connect(DB)
    rows = conn.execute("""
    select
      coalesce(source_ai,'') as source_ai,
      coalesce(decision,'') as decision,
      coalesce(matched_band,'') as matched_band,
      coalesce(sample_count,0) as sample_count,
      coalesce(avg_source_bias,0) as avg_source_bias,
      coalesce(avg_cluster_bias,0) as avg_cluster_bias
    from decider_feedback_metrics
    order by sample_count desc, source_ai asc, decision asc, matched_band asc
    """).fetchall()

    out = []
    for source_ai, decision, matched_band, sample_count, avg_source_bias, avg_cluster_bias in rows:
        sample_count = int(sample_count or 0)
        avg_source_bias = float(avg_source_bias or 0.0)
        avg_cluster_bias = float(avg_cluster_bias or 0.0)

        suggested_action = "keep"
        reason = "stable"

        if sample_count < 2:
            suggested_action = "observe"
            reason = "low_sample"

        elif decision == "execute_now" and matched_band in ("1_3", "4_7"):
            suggested_action = "consider_raise_execute_threshold"
            reason = "low_match_band_reaches_execute"

        elif decision == "backlog" and matched_band in ("13_plus",):
            suggested_action = "consider_lower_execute_threshold"
            reason = "high_match_band_stays_backlog"

        elif avg_cluster_bias >= 0.35 and decision == "execute_now":
            suggested_action = "consider_lower_cluster_cap"
            reason = "cluster_bias_dominant"

        elif avg_source_bias >= 0.30 and decision == "execute_now":
            suggested_action = "consider_lower_source_bias"
            reason = "source_bias_dominant"

        out.append((
            source_ai,
            decision,
            matched_band,
            sample_count,
            avg_source_bias,
            avg_cluster_bias,
            suggested_action,
            reason,
        ))

    conn.execute("delete from decider_threshold_advice")
    conn.executemany("""
    insert into decider_threshold_advice(
      source_ai, decision, matched_band,
      sample_count, avg_source_bias, avg_cluster_bias,
      suggested_action, suggestion_reason
    ) values(?,?,?,?,?,?,?,?)
    """, out)
    conn.commit()
    conn.close()
    print(f"decider_threshold_advice_done={len(out)}", flush=True)

if __name__ == "__main__":
    main()
