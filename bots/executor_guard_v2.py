import sqlite3,time,os

DB=os.environ.get("DB_PATH","data/openclaw_real.db")
PR_RATE_LIMIT=10

def pr_rate_ok(conn):
    cur=conn.cursor()
    cur.execute("""
        select count(*)
        from dev_proposals
        where coalesce(pr_url,'') <> ''
          and coalesce(created_at,'') > datetime('now','-1 hour')
    """)
    n=cur.fetchone()[0]
    return n < PR_RATE_LIMIT

while True:
    conn=sqlite3.connect(DB)
    cur=conn.cursor()

    print("=== Executor Guard v3 ===",flush=True)

    if not pr_rate_ok(conn):
        print("PR rate limit reached",flush=True)
        conn.close()
        time.sleep(60)
        continue

    cur.execute("""
        select id,title,branch_name
        from dev_proposals
        where coalesce(status,'') in ('approved','execute_now')
        order by id desc
        limit 10
    """)
    rows=cur.fetchall()

    for row in rows:
        print(row,flush=True)

    conn.close()
    time.sleep(60)
