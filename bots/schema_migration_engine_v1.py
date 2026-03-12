import os, sqlite3, time

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH")

def ensure():
    con = sqlite3.connect(DB, timeout=30)
    con.execute("pragma busy_timeout=30000")
    cur = con.cursor()

    cols = {r[1] for r in cur.execute("pragma table_info(dev_proposals)")}
    if "processing" not in cols:
        cur.execute("alter table dev_proposals add column processing integer default 0")

    cur.execute("create index if not exists idx_dev_proposals_pipeline on dev_proposals(status, dev_stage, pr_status)")
    cur.execute("create index if not exists idx_dev_proposals_pr_number on dev_proposals(pr_number)")
    cur.execute("create index if not exists idx_dev_proposals_pr_url on dev_proposals(pr_url)")

    con.commit()
    con.close()

while True:
    try:
        ensure()
    except Exception as e:
        print(repr(e), flush=True)
    time.sleep(30)
