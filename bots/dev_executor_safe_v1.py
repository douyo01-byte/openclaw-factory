import os, re, time, sqlite3, subprocess, traceback, datetime

DB_PATH=os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or "data/openclaw.db"
GH="/opt/homebrew/bin/gh"

def now():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat()+"Z"

def sh(args, capture=False):
    if capture:
        return subprocess.check_output(args, text=True).strip()
    subprocess.check_call(args)

def main():
    conn=sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory=sqlite3.Row
    row=conn.execute("""
        SELECT id,title,description
        FROM dev_proposals
        WHERE status='approved'
          AND (dev_stage IS NULL OR dev_stage='' OR dev_stage='approved')
        ORDER BY id ASC
        LIMIT 1
    """).fetchone()
    if not row:
        conn.close()
        return 0
    pid=row["id"]
    title=row["title"] or f"proposal {pid}"
    body=(row["description"] or "").strip() or "auto"

    try:
        b=f"auto-p{pid}"
        os.chdir(os.path.expanduser("~/AI/openclaw-factory"))
        sh(["git","fetch","-p","origin","main"])
        sh(["git","checkout","-f","main"])
        sh(["git","reset","--hard","origin/main"])
        sh(["git","clean","-fd"])
        sh(["git","checkout","-b",b])
        os.makedirs("dev_autogen", exist_ok=True)
        with open(f"dev_autogen/p{pid}.txt","w") as f:
            f.write(body+"\n")
        sh(["git","add","-A"])
        sh(["git","commit","-m",f"dev: proposal #{pid}"])
        sh(["git","push","-u","origin",b])

        pr_out=sh([GH,"pr","create","--title",f"[dev] proposal #{pid}","--body",body,"--base","main","--head",b], capture=True)
        pr_url=pr_out.splitlines()[-1].strip() if pr_out else ""
        m=re.search(r"/pull/(\d+)", pr_url)
        pr_num=int(m.group(1)) if m else None

        if (not pr_num) or ("/pull/" not in pr_url):
            conn.execute("""
                UPDATE dev_proposals
                SET status='hold',
                    dev_stage='hold',
                    pr_status='error',
                    pr_number=NULL,
                    pr_url=NULL,
                    dev_attempts=COALESCE(dev_attempts,0)+1
                WHERE id=?
            """,(pid,))
            conn.commit()
            return 0

        conn.execute("""
            UPDATE dev_proposals
            SET status='pr_created',
                dev_stage='pr_created',
                pr_number=?,
                pr_url=?,
                pr_status=COALESCE(pr_status,''),
                dev_attempts=COALESCE(dev_attempts,0)+1
            WHERE id=?
        """,(pr_num,pr_url,pid))
        conn.commit()
        return 0

    except Exception:
        try:
            conn.execute("""
                UPDATE dev_proposals
                SET status='hold',
                    dev_stage='hold',
                    pr_status='error',
                    dev_attempts=COALESCE(dev_attempts,0)+1
                WHERE id=?
            """,(pid,))
            conn.commit()
        except Exception:
            pass
        print(now(),"ERR pid",pid,flush=True)
        traceback.print_exc()
        return 1
    finally:
        conn.close()

if __name__=="__main__":
    raise SystemExit(main())
