import os,sqlite3,subprocess,re,time,json,sys

DB_PATH=os.environ.get("DB_PATH","data/openclaw.db")
REPO=os.environ.get("GITHUB_REPO","douyo01-byte/openclaw-factory")

def conn():
    return sqlite3.connect(DB_PATH,timeout=30)

def extract_pr_number(url):
    m=re.search(r'/pull/(\d+)',url or "")
    return int(m.group(1)) if m else None

def gh_pr_state(num):
    try:
        out=subprocess.check_output(
            ["gh","pr","view",str(num),"-R",REPO,"--json","state,mergedAt"],
            stderr=subprocess.DEVNULL
        )
        j=json.loads(out.decode())
        return j.get("state"),j.get("mergedAt")
    except:
        return None,None

def tick():
    c=conn()
    rows=c.execute("""
    select id,pr_number,pr_url,status,dev_stage
    from dev_proposals
    where pr_url is not null
    """).fetchall()
    for r in rows:
        pid,prn,url,status,stage=r
        if not prn and url:
            n=extract_pr_number(url)
            if n:
                c.execute("update dev_proposals set pr_number=? where id=?", (n,pid))
                prn=n
        if prn:
            state,mergedAt=gh_pr_state(prn)
            if state=="MERGED":
                c.execute("""
                update dev_proposals
                set status='merged',
                    dev_stage='merged',
                    pr_status='merged'
                where id=?
                """,(pid,))
    c.commit()
    c.close()

if __name__=="__main__":
    tick()
