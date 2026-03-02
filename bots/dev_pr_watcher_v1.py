import os,sqlite3,subprocess,re,json

DB_PATH=os.environ.get("DB_PATH","data/openclaw.db")
REPO=os.environ.get("GITHUB_REPO","douyo01-byte/openclaw-factory")

def conn():
    return sqlite3.connect(DB_PATH,timeout=30)

def ensure_tables(c):
    c.execute("""
    create table if not exists decision_memory(
      id integer primary key autoincrement,
      proposal_id integer,
      title text,
      refined_spec text,
      pr_url text,
      pr_number integer,
      result text,
      attempts integer default 1,
      created_at datetime default current_timestamp
    )
    """)

def extract_pr_number(url):
    m=re.search(r'/pull/(\d+)',url or "")
    return int(m.group(1)) if m else None

def gh_pr_state(num):
    try:
        out=subprocess.check_output(
            ["gh","pr","view",str(num),"-R",REPO,"--json","state"],
            stderr=subprocess.DEVNULL
        )
        j=json.loads(out.decode())
        return j.get("state")
    except:
        return None

def refined_spec_for(c,pid):
    row=c.execute("select refined_spec from dev_proposals where id=?", (pid,)).fetchone()
    return (row[0] if row else None) or ""

def learn(c,pid,title,pr_url,prn,result):
    refined=refined_spec_for(c,pid)
    c.execute("""
    insert into decision_memory(proposal_id,title,refined_spec,pr_url,pr_number,result,attempts,created_at)
    values(?,?,?,?,?,?,1,datetime('now'))
    """,(pid,title or "",refined,pr_url or "",prn,result))

def tick():
    c=conn()
    ensure_tables(c)

    rows=c.execute("""
    select id,pr_number,pr_url,status,title
    from dev_proposals
    where pr_url is not null
    """).fetchall()

    for pid,prn,url,status,title in rows:
        if not prn and url:
            n=extract_pr_number(url)
            if n:
                c.execute("update dev_proposals set pr_number=? where id=?", (n,pid))
                prn=n
        if prn:
            state=gh_pr_state(prn)
            if state=="MERGED" and status!="merged":
                c.execute("""
                update dev_proposals
                set status='merged',
                    dev_stage='merged',
                    pr_status='merged'
                where id=?
                """,(pid,))
                learn(c,pid,title,url,prn,"merged")

    c.commit()
    c.close()

if __name__=="__main__":
    tick()
