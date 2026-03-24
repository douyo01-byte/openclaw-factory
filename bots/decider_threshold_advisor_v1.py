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
        source_ai = str(source_ai or "").strip()
        decision = str(decision or "").strip()
        matched_band = str(matched_band or "").strip()
        sample_count = int(sample_count or 0)
        avg_source_bias = float(avg_source_bias or 0.0)
        avg_cluster_bias = float(avg_cluster_bias or 0.0)

        high_confidence = (
            sample_count >= 3
            and decision == "execute_now"
            and matched_band in ("8_12", "13_plus")
            and avg_source_bias >= 0.30
            and avg_cluster_bias <= 0.10
        )

        if sample_count < 3:
            suggested_action = "observe"
            suggestion_reason = "low_sample"
        elif high_confidence:
            suggested_action = "consider_lower_source_bias"
            suggestion_reason = "source_bias_dominant_high_confidence"
        else:
            suggested_action = "keep"
            suggestion_reason = "stable"

        out.append((
            source_ai,
            decision,
            matched_band,
            sample_count,
            avg_source_bias,
            avg_cluster_bias,
            suggested_action,
            suggestion_reason,
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
