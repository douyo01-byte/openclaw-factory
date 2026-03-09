import os,sqlite3,time
DB=os.environ["DB_PATH"]

def score(row):
    s=0
    t=(row["title"] or "").lower()
    c=(row["category"] or "").lower()
    a=(row["source_ai"] or "").lower()
    try:
        conf=float(row["confidence"] or 0)
    except:
        conf=0.0

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

    if c=="reliability":
        s+=24
    if c=="learning":
        s+=22
    if c=="automation":
        s+=20
    if c=="telemetry":
        s+=18
    if c=="infrastructure":
        s+=18
    if c=="cost":
        s+=16
    if c=="security":
        s+=26
    if c=="dev_experience":
        s+=17
    if c=="ai capability":
        s+=19
    if c=="performance":
        s+=24

    if a=="self_improve":
        s+=8
    if a=="revenue_brain":
        s+=6
    if a=="business_brain":
        s+=4
    if a=="market_brain":
        s+=4

    if conf>=0.9:
        s+=8
    elif conf>=0.8:
        s+=6
    elif conf>=0.7:
        s+=4
    elif conf>=0.6:
        s+=2

    return s

def run():
    conn=sqlite3.connect(DB)
    conn.row_factory=sqlite3.Row
    rows=conn.execute("""
    select id,title,status,category,source_ai,confidence
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
