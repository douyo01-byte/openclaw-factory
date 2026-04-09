import os
import sqlite3
from bots.fortune_engine_v1 import generate_reading

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))

def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    trial = cur.execute("""
    select id from money_trials
    where theme='AI占い'
    order by priority desc, id asc
    limit 1
    """).fetchone()

    if not trial:
        print("trial_missing", flush=True)
        return

    trial_id = trial[0]

    args = {
        "name": "D.kid",
        "birth_date": "1990-01-01",
        "question": "今やるべきことは何か",
        "birth_time": "",
        "birth_place": "",
    }

    r1 = generate_reading(**args)
    r2 = generate_reading(**args)

    consistent = int(r1["output_hash"] == r2["output_hash"])
    score = 30 if consistent else -50

    cur.execute("""
    insert into money_results(trial_id, action_id, metric_type, metric_value, score_delta)
    values(?,?,?,?,?)
    """, (
        trial_id,
        None,
        "consistency_check",
        str(consistent),
        score
    ))

    cur.execute("""
    update money_trials
    set score=score+?, updated_at=datetime('now')
    where id=?
    """, (score, trial_id))

    con.commit()
    con.close()
    print(f"consistency={consistent} trial_id={trial_id}", flush=True)

if __name__ == "__main__":
    main()
