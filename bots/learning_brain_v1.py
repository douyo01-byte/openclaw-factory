import sqlite3,os,time

DB=os.environ["DB_PATH"]

def evaluate(row):
    title=(row["title"] or "").lower()
    pr=row["pr_number"]

    if "guard" in title or "safety" in title:
        return "success",0.9,"safety improvement"

    if "logging" in title:
        return "neutral",0.6,"internal improvement"

    if "rollback" in title or "revert" in title:
        return "bad",0.2,"rollback detected"

    return "success",0.8,"normal merged change"

while True:
    conn=sqlite3.connect(DB)
    conn.row_factory=sqlite3.Row

    rows=conn.execute("""
    select *
    from dev_proposals
    where pr_status='merged'
    and result_type is null
    """).fetchall()

    for r in rows:

        rtype,score,note=evaluate(r)

        conn.execute("""
        update dev_proposals
        set result_type=?,
            result_score=?,
            result_note=?
        where id=?
        """,(rtype,score,note,r["id"]))

        conn.execute("""
        insert or ignore into decision_patterns(token,weight)
        values (?,?)
        """,(rtype,score))

    conn.commit()

    top=conn.execute("""
    select id,title,result_type,result_score
    from dev_proposals
    where pr_status='merged'
    order by id desc
    limit 10
    """).fetchall()

    print("\n=== Learning Brain v1 ===\n",flush=True)

    for t in top:
        print(tuple(t),flush=True)

    conn.close()
    time.sleep(120)
