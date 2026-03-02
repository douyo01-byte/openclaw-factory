import os,sqlite3,subprocess,json,datetime

DB_PATH=os.environ.get("DB_PATH","data/openclaw.db")
REPO=os.environ.get("GITHUB_REPO","douyo01-byte/openclaw-factory")
CORE_PATH=os.path.expanduser("~/AI/openclaw-factory")

def conn():
    return sqlite3.connect(DB_PATH,timeout=30)

def sh(cmd,cwd=None,timeout=120):
    return subprocess.run(cmd,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout,text=True)

def gh_pr(num):
    r=sh(["gh","pr","view",str(num),"-R",REPO,"--json","number,headRefName"],timeout=20)
    if r.returncode!=0:
        return None
    return json.loads(r.stdout)

def run_fix_suite():
    sh(["git","fetch","--prune","origin"],cwd=CORE_PATH,timeout=60)
    sh(["git","status","--porcelain"],cwd=CORE_PATH,timeout=20)
    sh(["python","-m","compileall","-q","."],cwd=CORE_PATH,timeout=120)
    sh(["ruff","check","--fix","."],cwd=CORE_PATH,timeout=180)
    sh(["black","."],cwd=CORE_PATH,timeout=180)
    sh(["pytest","-q"],cwd=CORE_PATH,timeout=240)

def has_changes():
    r=sh(["git","status","--porcelain"],cwd=CORE_PATH,timeout=20)
    return r.stdout.strip()!=""

def commit_push(branch):
    sh(["git","add","-A"],cwd=CORE_PATH,timeout=60)
    ts=datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    sh(["git","commit","-m",f"ci: auto fix ({ts})"],cwd=CORE_PATH,timeout=60)
    sh(["git","push","origin",branch],cwd=CORE_PATH,timeout=120)

def rerun_ci(branch):
    sh(["gh","workflow","run","ci.yml","-R",REPO,"--ref",branch],timeout=20)

def ensure_tables(c):
    c.execute("""
    create table if not exists auto_fix_log(
      proposal_id integer primary key,
      pr_number integer,
      last_fix_at text,
      fix_count integer default 0
    )
    """)

def tick():
    c=conn()
    ensure_tables(c)

    rows=c.execute("""
    select p.id,p.pr_number,p.pr_url,p.dev_stage,cr.failure_reason,coalesce(l.fix_count,0)
    from dev_proposals p
    left join ci_retry cr on cr.proposal_id=p.id
    left join auto_fix_log l on l.proposal_id=p.id
    where p.pr_number is not null
      and p.dev_stage='ci_failed'
    order by p.id desc
    limit 5
    """).fetchall()

    for pid,prn,pr_url,stage,reason,fix_count in rows:
        if fix_count>=2:
            continue

        info=gh_pr(prn)
        if not info:
            continue
        branch=info.get("headRefName") or ""
        if not branch:
            continue

        sh(["git","checkout","-f",branch],cwd=CORE_PATH,timeout=30)
        sh(["git","reset","--hard",f"origin/{branch}"],cwd=CORE_PATH,timeout=60)
        run_fix_suite()

        if has_changes():
            commit_push(branch)
            rerun_ci(branch)

        now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""
        insert into auto_fix_log(proposal_id,pr_number,last_fix_at,fix_count)
        values(?,?,?,?)
        on conflict(proposal_id) do update set
          pr_number=excluded.pr_number,
          last_fix_at=excluded.last_fix_at,
          fix_count=auto_fix_log.fix_count+1
        """,(pid,prn,now,fix_count+1))

        c.execute("update dev_proposals set dev_stage='ci_retrying' where id=?", (pid,))

    c.commit()
    c.close()

if __name__=="__main__":
    tick()
