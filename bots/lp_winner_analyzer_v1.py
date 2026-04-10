from __future__ import annotations
import json
import os
import sqlite3

DB_PATH = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def main():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    row = cur.execute("""
        select variant, views, unlocks, score
        from lp_variants
        order by score desc, unlocks desc, views desc, variant asc
        limit 1
    """).fetchone()

    if not row:
        print("no_lp_variant_row")
        con.close()
        return

    payload = {
        "variant": row["variant"],
        "views": int(row["views"] or 0),
        "unlocks": int(row["unlocks"] or 0),
        "score": float(row["score"] or 0),
    }

    cols = {r["name"] for r in cur.execute("pragma table_info(learning_results)").fetchall()}

    data = {
        "proposal_id": -3000000000,
        "title": f"lp winner pattern {payload['variant']}",
        "source_ai": "lp_system",
        "target_system": "lp_autopilot",
        "improvement_type": "win_pattern",
        "impact_score": 0.4,
        "impact_level": "internal",
        "impact_reason": "lp winner captured",
        "result_score": payload["score"],
        "result_type": "win_pattern",
        "result_note": json.dumps(payload, ensure_ascii=False),
        "success_flag": 1,
        "learning_summary": json.dumps(payload, ensure_ascii=False),
        "merged_at": "",
        "created_at": "datetime('now')",
    }

    use_cols = []
    vals = []
    sql_vals = []

    for k, v in data.items():
        if k not in cols:
            continue
        use_cols.append(k)
        if isinstance(v, str) and v == "datetime('now')":
            sql_vals.append("datetime('now')")
        else:
            sql_vals.append("?")
            vals.append(v)

    if use_cols:
        cur.execute(
            f"""
            insert into learning_results({",".join(use_cols)})
            values({",".join(sql_vals)})
            """,
            tuple(vals),
        )
        con.commit()
        print("winner_pattern_logged")
    else:
        print("learning_results_no_compatible_columns")

    con.close()

if __name__ == "__main__":
    main()
