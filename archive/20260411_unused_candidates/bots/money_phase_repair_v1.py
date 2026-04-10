import os
import sqlite3

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))

def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    row = cur.execute("""
    select id, phase, score
    from money_trials
    where id=1
    """).fetchone()

    if not row:
        print("trial_missing", flush=True)
        return

    trial_id, phase, score = row

    if phase == "improve" and score >= 100:
        cur.execute("""
        update money_trials
        set phase='measure', updated_at=datetime('now')
        where id=?
        """, (trial_id,))
        print(f"phase_repaired trial_id={trial_id} improve->measure", flush=True)
    else:
        print(f"phase_nochange trial_id={trial_id} phase={phase} score={score}", flush=True)

    con.commit()
    con.close()

if __name__ == "__main__":
    main()
