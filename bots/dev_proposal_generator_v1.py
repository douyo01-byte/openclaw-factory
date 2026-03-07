import sqlite3
import datetime
import random
import time

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
    cur.execute(
        """insert into dev_proposals(title,description,branch_name,status)
           values(?,?,?,?)""",
        (t[0], t[1], "__tmp__", "approved"),
    )
    pid = cur.lastrowid
    ts = int(time.time() * 1000)
    branch = f"{t[2]}-{pid}-{ts}"
    cur.execute(
        "update dev_proposals set branch_name=? where id=?",
        (branch, pid),
    )
    conn.commit()
    print("proposal created", pid, branch)

if __name__ == "__main__":
    main()
