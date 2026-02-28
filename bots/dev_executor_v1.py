from __future__ import annotations
import json, os, re, sqlite3, subprocess, sys
from datetime import datetime, timezone

DB_PATH=os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or "data/openclaw.db"
BASE_BRANCH=os.environ.get("GIT_BASE_BRANCH") or "main"

def sh(args, check=True, capture=False):
    if capture:
        p=subprocess.run(args, check=check, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        return p.stdout.strip()
    subprocess.run(args, check=check)

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def main():
    conn=sqlite3.connect(DB_PATH)
    conn.row_factory=sqlite3.Row
    row=conn.execute(
        """
        SELECT id,title,description,pr_number,pr_url,dev_stage,dev_attempts
        FROM dev_proposals
        WHERE status='approved'
          AND (pr_number IS NULL OR pr_number='')
          AND (dev_stage IS NULL OR dev_stage='' OR dev_stage='approved')
        ORDER BY id ASC
        LIMIT 1
        """
    ).fetchone()
    if not row:
        print("no approved proposals")
        return 0

    pid=int(row["id"])
    title=(row["title"] or f"proposal {pid}").strip()
    description=(row["description"] or "").strip()
    branch=f"dev/p{pid}"
    out=sh(["git","rev-parse","--abbrev-ref","HEAD"], capture=True)
    if out != BASE_BRANCH:
        sh(["git","checkout",BASE_BRANCH])

    sh(["git","pull","--rebase","origin",BASE_BRANCH])

    exists=sh(["git","ls-remote","--heads","origin",branch], capture=True)
    if exists:
        sh(["git","checkout",branch])
        sh(["git","pull","--rebase","origin",branch])
    else:
        sh(["git","checkout","-b",branch])

    dpath=f"dev_autogen"
    fpath=f"{dpath}/p{pid}.txt"
    sh(["mkdir","-p",dpath], check=True)
    with open(fpath,"w",encoding="utf-8") as f:
        f.write(f"id={pid}\n")
        f.write(f"title={title}\n")
        f.write(f"ts={now()}\n")
        if description:
            f.write("\n")
            f.write(description[:4000] + "\n")

    sh(["git","add",fpath])
    diff=sh(["git","status","--porcelain"], capture=True)
    if not diff:
        print("nothing to commit")
        return 0

    sh(["git","commit","-m",f"dev: proposal #{pid} bootstrap PR"])
    sh(["git","push","-u","origin",branch])

    prj=sh(["gh","pr","create","--base",BASE_BRANCH,"--head",branch,"--title",f"[dev] {title} (#{pid})","--body",f"proposal_id: {pid}\n\n{description}"], capture=True)
    pr_url=prj.strip().splitlines()[-1].strip()
    pr_num=None
    m=re.search(r"/pull/(\d+)", pr_url)
    if m:
        pr_num=int(m.group(1))

    conn.execute(
        """
        UPDATE dev_proposals
        SET dev_stage='pr_created',
            pr_number=COALESCE(?, pr_number),
            pr_url=COALESCE(?, pr_url),
            dev_attempts=COALESCE(dev_attempts,0)+1
        WHERE id=?
        """,
        (pr_num, pr_url, pid),
    )
    conn.commit()
    print(json.dumps({"proposal_id": pid, "branch": branch, "pr_number": pr_num, "pr_url": pr_url}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
