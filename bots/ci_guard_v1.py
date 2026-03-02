import os,sqlite3,subprocess,json,re,datetime

DB_PATH=os.environ.get("DB_PATH",os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))
REPO=os.environ.get("GITHUB_REPO","douyo01-byte/openclaw-factory")

def conn():
    return sqlite3.connect(DB_PATH,timeout=30)

def ensure_tables(c):
    c.execute("""
    create table if not exists ci_retry(
      proposal_id integer primary key,
      pr_number integer,
      head_ref text,
      retry_count integer default 0,
      last_conclusion text,
      last_checked_at text,
      last_run_id text,
      failure_reason text
    )
    """)

def extract_pr_number(url):
    m=re.search(r'/pull/(\d+)',url or "")
    return int(m.group(1)) if m else None

def gh_pr(num):
    out=subprocess.check_output([
"gh","pr","view",str(num),"-R",REPO,"--json","number,headRefName,statusCheckRollup"], stderr=subprocess.DEVNULL, timeout=10)
    j=json.loads(out.decode())
    return j

def first_fail_reason(j):
    roll=j.get("statusCheckRollup") or []
    for x in roll:
        c=x.get("conclusion")
        if c in ("FAILURE","CANCELLED","TIMED_OUT","ACTION_REQUIRED"):
            n=x.get("name") or ""
            return (c+":"+n) if n else c
    return ""

def conclusion_from_rollup(j):
    roll=j.get("statusCheckRollup") or []
    concl=[]
    for x in roll:
        c=x.get("conclusion")
        s=x.get("status")
        if c: concl.append(c)
        elif s: concl.append(s)
    if any(x in ("FAILURE","CANCELLED","TIMED_OUT","ACTION_REQUIRED") for x in concl):
        return "FAIL"
    if any(x in ("PENDING","IN_PROGRESS","QUEUED","REQUESTED","WAITING") for x in concl):
        return "PENDING"
    if concl and all(x in ("SUCCESS","SKIPPED","NEUTRAL") for x in concl):
        return "PASS"
    return "UNKNOWN"

def rerun_ci(head_ref):
    try:
        out=subprocess.check_output([
"gh","workflow","run","ci.yml","-R",REPO,"--ref",head_ref], stderr=subprocess.DEVNULL, timeout=10)
        m=re.search(r'https://github\.com/.*/actions/runs/(\d+)',out.decode())
        return m.group(1) if m else ""
    except:
        return ""

def tick():
    c=conn()
    ensure_tables(c)

    rows=c.execute("""
    select id,pr_number,pr_url,status,dev_stage
    from dev_proposals
    where pr_url is not null
      and (status is null or status!='merged')
    """).fetchall()

    for pid,prn,url,status,stage in rows:
        if not prn:
            prn=extract_pr_number(url)
            if prn:
                c.execute("update dev_proposals set pr_number=? where id=?", (prn,pid))
        if not prn:
            continue

        try:
            j=gh_pr(prn)
        except:
            continue

        head=j.get("headRefName") or ""
        concl=conclusion_from_rollup(j)
        reason=first_fail_reason(j)
        now=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        cur=c.execute("select retry_count,last_conclusion from ci_retry where proposal_id=?", (pid,)).fetchone()
        if cur:
            retry_count,last_conclusion=cur
        else:
            retry_count,last_conclusion=0,""

        if concl in ("PASS","PENDING","UNKNOWN"):
            c.execute("""
            insert into ci_retry(proposal_id,pr_number,head_ref,retry_count,last_conclusion,last_checked_at,last_run_id,failure_reason)
            values(?,?,?,?,?,?,?,?)
            on conflict(proposal_id) do update set
              pr_number=excluded.pr_number,
              head_ref=excluded.head_ref,
              last_conclusion=excluded.last_conclusion,
              last_checked_at=excluded.last_checked_at,
              failure_reason=excluded.failure_reason
            """,(pid,prn,head,retry_count,concl,now,"",reason))
            if stage in ("ci_failed","ci_retrying"):
                c.execute("update dev_proposals set dev_stage='' where id=?", (pid,))
            continue

        if concl=="FAIL":
            if retry_count < 3:
                run_id=rerun_ci(head)
                retry_count+=1
                c.execute("""
                insert into ci_retry(proposal_id,pr_number,head_ref,retry_count,last_conclusion,last_checked_at,last_run_id,failure_reason)
                values(?,?,?,?,?,?,?,?)
                on conflict(proposal_id) do update set
                  pr_number=excluded.pr_number,
                  head_ref=excluded.head_ref,
                  retry_count=excluded.retry_count,
                  last_conclusion=excluded.last_conclusion,
                  last_checked_at=excluded.last_checked_at,
                  last_run_id=excluded.last_run_id,
                  failure_reason=excluded.failure_reason
                """,(pid,prn,head,retry_count,concl,now,run_id,reason))
                c.execute("update dev_proposals set dev_stage='ci_retrying' where id=?", (pid,))
            else:
                c.execute("""
                insert into ci_retry(proposal_id,pr_number,head_ref,retry_count,last_conclusion,last_checked_at,last_run_id,failure_reason)
                values(?,?,?,?,?,?,?,?)
                on conflict(proposal_id) do update set
                  pr_number=excluded.pr_number,
                  head_ref=excluded.head_ref,
                  last_conclusion=excluded.last_conclusion,
                  last_checked_at=excluded.last_checked_at
                """,(pid,prn,head,retry_count,concl,now,"",reason))
                c.execute("update dev_proposals set dev_stage='ci_failed' where id=?", (pid,))

    c.commit()
    c.close()

if __name__=="__main__":
    tick()
