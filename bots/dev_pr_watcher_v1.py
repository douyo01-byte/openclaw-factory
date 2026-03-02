import os,sqlite3,subprocess,re,json,sys

DB_PATH=os.environ.get("DB_PATH","data/openclaw.db")
REPO=os.environ.get("GITHUB_REPO","douyo01-byte/openclaw-factory")
CORE_DB=os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db")

def conn():
    return sqlite3.connect(DB_PATH,timeout=30)

def core_conn():
    return sqlite3.connect(CORE_DB,timeout=30)

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

def learn(pid):
    c=core_conn()
    row=c.execute("""
    select title,description from dev_proposals where id=?
    """,(pid,)).fetchone()
    if not row:
        c.close()
        return
    title,desc=row
    c.execute("""
    insert into decision_patterns(kind,content,created_at)
    values('merged',?,datetime('now'))
    """,(f"{title}\n{desc}",))
    c.commit()
    c.close()

def tick():
    c=conn()
    rows=c.execute("""
    select id,pr_number,pr_url,status from dev_proposals
    where pr_url is not null
    """).fetchall()
    for pid,prn,url,status in rows:
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
                learn(pid)
    c.commit()
    c.close()

if __name__=="__main__":
    tick()
