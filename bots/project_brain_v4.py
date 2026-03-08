import os,sqlite3,time

DB=os.environ["DB_PATH"]

def score(row):
    s=0
    t=(row["title"] or "").lower()

    if "security" in t:
        s+=50
    if "performance" in t:
        s+=40
    if "optimize" in t:
        s+=30
    if "cache" in t:
        s+=25
    if "dashboard" in t:
        s+=20
    if "log" in t:
        s+=10

    return s

def run():
    conn=sqlite3.connect(DB)
    conn.row_factory=sqlite3.Row

    rows=conn.execute("""
    select id,title,status
    from dev_proposals
    where status='approved'
    """).fetchall()

    for r in rows:
        sc=score(r)

        conn.execute("""
        update dev_proposals
        set priority=?
        where id=?
        """,(sc,r["id"]))

    conn.commit()
    conn.close()

if __name__=="__main__":
    while True:
        run()
        time.sleep(60)
