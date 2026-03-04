from __future__ import annotations
import os, re, sqlite3, subprocess, time, traceback
from datetime import datetime, timezone

DB_PATH=os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or (os.path.expanduser("~/AI/openclaw-factory-daemon/data/openclaw.db"))
GH="/opt/homebrew/bin/gh"

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def gh(args):
    env=dict(os.environ)
    env["PATH"]="/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    p=subprocess.run([GH]+args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    if p.returncode!=0:
        raise RuntimeError(p.stdout.strip())
    return p.stdout.strip()

def extract_pr(pr_url: str|None):
    if not pr_url:
        return None
    m=re.search(r"/pull/(\d+)", pr_url)
    if not m:
        return None
    return int(m.group(1))

def loop():
    while True:
        try:
            con=sqlite3.connect(DB_PATH, timeout=30)
            con.row_factory=sqlite3.Row

            rows=con.execute("""
                select id, pr_number, pr_url, coalesce(pr_status,'') as pr_status
                from dev_proposals
                where status='pr_created'
                  and coalesce(pr_status,'')!='merged'
                order by id asc
                limit 200
            """).fetchall()

            touched=0
            for r in rows:
                pid=int(r["id"])
                pr=r["pr_number"]
                pr_url=r["pr_url"]
                if not pr:
                    pr=extract_pr(pr_url)
                    if pr:
                        con.execute("update dev_proposals set pr_number=? where id=?", (pr, pid))
                        con.commit()

                if not pr:
                    continue

                state=gh(["pr","view",str(pr),"--json","state","-q",".state"]).strip()
                st=state.lower()

                if state=="MERGED":
                    con.execute("""
                        update dev_proposals
                        set status='merged',
                            dev_stage='merged',
                            pr_status='merged'
                        where id=?
                    """,(pid,))
                    con.commit()
                    touched+=1
                else:
                    if st and st!=r["pr_status"]:
                        con.execute("update dev_proposals set pr_status=? where id=?", (st, pid))
                        con.commit()
                        touched+=1

            print(now(),"checked",len(rows),"touched",touched,flush=True)
            con.close()

        except Exception:
            print("ERR",flush=True)
            traceback.print_exc()

        time.sleep(5)

if __name__=="__main__":
    loop()
