import sqlite3,os,time,subprocess

DB=os.environ["DB_PATH"]

def merge_all():
    try:
        subprocess.run(
            ["gh","pr","list","--json","number","-q",".[] .number"],
            capture_output=True
        )
    except:
        pass

while True:

    conn=sqlite3.connect(DB)
    conn.row_factory=sqlite3.Row

    merged=conn.execute("""
    SELECT count(*) c
    FROM dev_proposals
    WHERE pr_status='merged'
    """).fetchone()["c"]

    open_pr=conn.execute("""
    SELECT count(*) c
    FROM dev_proposals
    WHERE pr_status='open'
    """).fetchone()["c"]

    approved=conn.execute("""
    SELECT count(*) c
    FROM dev_proposals
    WHERE status='approved'
    """).fetchone()["c"]

    print("\n=== OpenClaw MotherShip v2 ===\n")

    print("merged:",merged)
    print("open_pr:",open_pr)
    print("approved:",approved)

    if open_pr>5:
        print("PR queue high -> merge attempt")
        subprocess.run(
            "gh pr list --json number -q '.[].number' | while read n; do gh pr merge $n --squash --delete-branch || true; done",
            shell=True
        )

    if approved>5:
        print("executor backlog detected")

    conn.close()

    time.sleep(60)
