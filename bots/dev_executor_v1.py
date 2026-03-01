from __future__ import annotations
import json, os, re, sqlite3, subprocess
from datetime import datetime, timezone

DB_PATH=os.environ.get("OCLAW_DB_PATH","/Users/doyopc/AI/openclaw-factory/data/openclaw.db")
BASE_BRANCH="main"
REPO="/Users/doyopc/AI/openclaw-factory"

KAI_LOG=os.path.join(REPO,"logs","kai_actions.log")
def sh(args,capture=False):
    env=dict(os.environ)
    env["HOME"]="/Users/doyopc"
    env["PATH"]="/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    if capture:
        p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,cwd=REPO,env=env)
        return p.stdout.strip()
    subprocess.run(args,cwd=REPO,env=env,check=True)

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def kai(conn, pid, event, **kw):
    os.makedirs(os.path.dirname(KAI_LOG), exist_ok=True)
    payload={"ts": now(), "proposal_id": pid, "event": event, **kw}
    with open(KAI_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    conn.execute(
        "INSERT INTO dev_events (proposal_id,event_type,payload) VALUES (?,?,?)",
        (pid, event, json.dumps(payload, ensure_ascii=False)),
    )

def main():
    os.makedirs(os.path.dirname(DB_PATH),exist_ok=True)
    conn=sqlite3.connect(DB_PATH,timeout=30)
    conn.row_factory=sqlite3.Row
    row=conn.execute("""
        SELECT id,title,description,branch_name,pr_number,pr_url,dev_stage,dev_attempts
        FROM dev_proposals
        WHERE status='approved'
AND (dev_stage IS NULL OR dev_stage='' OR dev_stage='approved')
        ORDER BY id ASC
        LIMIT 1
    """).fetchone()
    if not row:
        raise SystemExit("no approved proposals")
        return 0
    pid=int(row["id"])
    kai(conn,pid,"picked",branch_name=(row["branch_name"] or ""),title=(row["title"] or ""))
    title=(row["title"] or f"proposal {pid}").strip()
    branch=row["branch_name"] or f"dev/proposal-{pid}"
    description=row["description"] or ""
    sh(["/usr/bin/git","checkout",BASE_BRANCH])
    kai(conn,pid,"git_base",base=BASE_BRANCH)
    sh(["/usr/bin/git","fetch","origin",BASE_BRANCH])
    sh(["/usr/bin/git","reset","--hard","origin/"+BASE_BRANCH])
    sh(["/usr/bin/git","clean","-fd"])
    exists=sh(["/usr/bin/git","ls-remote","--heads","origin",branch],capture=True)
    if exists:
        sh(["/usr/bin/git","checkout",branch])
        sh(["/usr/bin/git","fetch","origin",branch])
        sh(["/usr/bin/git","reset","--hard","origin/"+branch])
        sh(["/usr/bin/git","clean","-fd"])
    else:
        sh(["/usr/bin/git","checkout","-B",branch])
    os.makedirs(os.path.join(REPO,"dev_autogen"),exist_ok=True)
    fpath=os.path.join(REPO,"dev_autogen",f"p{pid}.txt")
    with open(fpath,"w",encoding="utf-8") as f:
        f.write(f"id={pid}\n")
        f.write(f"title={title}\n")
        f.write(f"ts={now()}\n\n")
        f.write(description[:4000])
    sh(["/usr/bin/git","add",fpath])
    sh(["/usr/bin/git","commit","-m",f"dev: proposal #{pid} bootstrap PR"])
    sh(["/usr/bin/git","push","-u","origin",branch])
    kai(conn,pid,"git_push",branch=branch)
    prj=sh(["/opt/homebrew/bin/gh","pr","create","--base",BASE_BRANCH,"--head",branch,"--title",f"[dev] {title} (#{pid})","--body",f"proposal_id: {pid}\nbranch: {branch}\n\n{description}"],capture=True)
    pr_url=prj.strip().splitlines()[-1].strip()
    pr_num=None
    m=re.search(r"/pull/(\\d+)",pr_url)
    if m: pr_num=int(m.group(1))
    conn.execute("""
        UPDATE dev_proposals
        SET dev_stage='pr_created',
            pr_number=COALESCE(?,pr_number),
            pr_url=COALESCE(?,pr_url),
            dev_attempts=COALESCE(dev_attempts,0)+1
        WHERE id=?
    """,(pr_num,pr_url,pid))
    kai(conn,pid,"db_updated",pr_url=pr_url,pr_number=pr_num)
    conn.commit()
    print(json.dumps({"proposal_id":pid,"branch":branch,"pr_number":pr_num,"pr_url":pr_url},ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
