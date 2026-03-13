import sqlite3,os,time,subprocess

DB=os.environ.get("DB_PATH","")

def count(q):
    conn=sqlite3.connect(DB)
    c=conn.execute(q).fetchone()[0]
    conn.close()
    return c

while True:

    merged=count("""
    SELECT count(*)
    FROM dev_proposals
    WHERE pr_status='merged'
    """)

    open_pr=count("""
    SELECT count(*)
    FROM dev_proposals
    WHERE pr_status='open'
    """)

    approved=count("""
    SELECT count(*)
    FROM dev_proposals
    WHERE status='approved'
    """)

    total=count("""
    SELECT count(*)
    FROM dev_proposals
    """)

    print("\033c")

    print("========== OpenClaw Dashboard ==========\n")

    print("Total Proposals :",total)
    print("Merged          :",merged)
    print("Open PR         :",open_pr)
    print("Approved Queue  :",approved)

    print("\n--- Latest proposals ---\n")

    conn=sqlite3.connect(DB)

    for r in conn.execute("""
    SELECT id,title,pr_status
    FROM dev_proposals
    ORDER BY id DESC
    LIMIT 10
    """):
        print(r)

    conn.close()

    print("\nRefresh in 5s")

    time.sleep(5)
