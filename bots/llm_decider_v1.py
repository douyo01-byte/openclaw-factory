import sqlite3,os,time

DB=os.environ["DB_PATH"]

def decide(row):
    title=(row["title"] or "").lower()
    brain=(row["brain_type"] or "").lower()
    priority=float(row["priority"] or 0)

    if priority >= 5:
        return "execute_now","high priority revenue/market proposal"
    if "safety" in title or "watcher" in title or "logging" in title:
        return "backlog","useful internal improvement but not top priority"
    if priority <= 0:
        return "archive","low signal proposal"
    if brain=="internal":
        return "backlog","internal improvement kept for later"
    return "backlog","default keep decision"

while True:
    conn=sqlite3.connect(DB)
    conn.row_factory=sqlite3.Row

    rows=conn.execute("""
    select id,title,brain_type,priority
    from dev_proposals
    where status='approved'
    order by priority desc,id desc
    limit 20
    """).fetchall()

    for r in rows:
        d,n=decide(r)
        conn.execute("""
        update dev_proposals
        set project_decision=?,
            decision_note=?
        where id=?
        """,(d,n,r["id"]))

    conn.commit()

    top=conn.execute("""
    select id,title,priority,project_decision,decision_note
    from dev_proposals
    where status='approved'
    order by priority desc,id desc
    limit 10
    """).fetchall()

    print("\n=== LLM Decider v1 ===\n",flush=True)
    for t in top:
        print(tuple(t),flush=True)

    conn.close()
    time.sleep(60)
