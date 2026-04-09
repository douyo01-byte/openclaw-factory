import os
import sqlite3

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))

def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    row = cur.execute("""
    select id from money_trials
    where theme='AI占い' and product_type='ai_fortune'
    order by id asc
    limit 1
    """).fetchone()

    if not row:
        cur.execute("""
        insert into money_trials(theme,hypothesis,product_type,status,phase,priority,notes)
        values(?,?,?,?,?,?,?)
        """, (
            "AI占い",
            "多占学統合・同一入力同一結果・無人納品のAI占いは販売可能性が高い",
            "ai_fortune",
            "testing",
            "design",
            95,
            "seeded by money_trial_seed_v1"
        ))
        trial_id = cur.lastrowid
    else:
        trial_id = row[0]

    exists = cur.execute("""
    select 1 from money_results
    where trial_id=? and metric_type='seed_ready'
    limit 1
    """, (trial_id,)).fetchone()

    if not exists:
        cur.execute("""
        insert into money_results(trial_id, action_id, metric_type, metric_value, score_delta)
        values(?,?,?,?,?)
        """, (trial_id, None, "seed_ready", "1", 5))

    con.commit()
    con.close()
    print(f"seeded_trial={trial_id}", flush=True)

if __name__ == "__main__":
    main()
