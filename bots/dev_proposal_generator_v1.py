import sqlite3
import datetime
import random

DB = "data/openclaw.db"

IDEAS = [
    ("Improve Research Quality", "Add better search sources", "dev/idea-a"),
    ("Optimize Costs", "Add cost estimator", "dev/idea-b"),
    ("Speed Pipeline", "Parallelize jobs", "dev/idea-c"),
]

def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    t = random.choice(IDEAS)
    ts = int(datetime.datetime.now(datetime.UTC).timestamp() * 1000)
    cur.execute(
        "insert into dev_proposals(title,description,spec,branch_name,status) values(?,?,?,?,?)",
        (t[0], t[1], t[1], f"{t[2]}-{ts}", "approved"),
    )
    conn.commit()
    print("proposal created", cur.lastrowid, f"{t[2]}-{ts}")

if __name__ == "__main__":
    main()
