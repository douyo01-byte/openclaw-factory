import sqlite3,os,time,re,hashlib

DB=os.environ["DB_PATH"]

def norm(s):
    s=(s or "").lower().strip()
    s=re.sub(r'[^a-z0-9]+',' ',s)
    s=re.sub(r'\s+',' ',s).strip()
    return s

def cluster_key(row):
    t=norm(row["title"])
    d=norm(row["description"])
    seed=(t+" "+d).strip()
    words=seed.split()[:6]
    if not words:
        return "cluster-empty"
    base=" ".join(words)
    h=hashlib.sha1(base.encode()).hexdigest()[:10]
    return "cl-"+h

def priority_score(row):
    score=0.0
    brain=row["brain_type"]
    conf=row["confidence"]

    if brain=="revenue":
        score+=5
    elif brain=="market":
        score+=3
    elif brain=="business":
        score+=2
    elif brain=="internal":
        score+=1

    if conf is not None:
        score+=float(conf)

    title=(row["title"] or "").lower()
    if "dashboard" in title:
        score+=0.5
    if "safety" in title or "guard" in title:
        score+=0.3

    return score

while True:
    conn=sqlite3.connect(DB)
    conn.row_factory=sqlite3.Row

    rows=conn.execute("""
    select *
    from dev_proposals
    where status='approved'
    order by id asc
    """).fetchall()

    clusters={}

    for r in rows:
        pid=r["id"]
        score=priority_score(r)
        cid=cluster_key(r)

        conn.execute(
            "update dev_proposals set priority=?, cluster_id=? where id=?",
            (score,cid,pid)
        )

        if cid not in clusters:
            clusters[cid]=(pid,score)
            decision="execute_now" if score>=3 else "backlog"
            conn.execute("""
            update dev_proposals
            set project_decision=?,
                duplicate_of=NULL,
                cluster_role='master'
            where id=?
            """,(decision,pid))
        else:
            master_id,master_score=clusters[cid]
            if score>master_score:
                conn.execute("""
                update dev_proposals
                set project_decision='duplicate',
                    duplicate_of=?,
                    cluster_role='member'
                where id=?
                """,(pid,master_id))
                conn.execute("""
                update dev_proposals
                set project_decision='execute_now',
                    duplicate_of=NULL,
                    cluster_role='master'
                where id=?
                """,(pid,))
                clusters[cid]=(pid,score)
            else:
                role='member'
                decision='duplicate' if score>=1 else 'backlog'
                conn.execute("""
                update dev_proposals
                set project_decision=?,
                    duplicate_of=?,
                    cluster_role=?
                where id=?
                """,(decision,master_id,role,pid))

    conn.commit()

    top=conn.execute("""
    select id,title,priority,cluster_id,cluster_role,project_decision,coalesce(duplicate_of,'')
    from dev_proposals
    where status='approved'
    order by priority desc,id desc
    limit 15
    """).fetchall()

    print("\n=== Project Brain v3 ===\n",flush=True)
    for t in top:
        print(tuple(t),flush=True)

    conn.close()
    time.sleep(60)
