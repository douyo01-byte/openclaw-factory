import os,sqlite3,time,subprocess,json

DB=os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or "data/openclaw_real.db"
ROOT="/Users/doyopc/AI/openclaw-factory-daemon"

def run(cmd):
  return subprocess.check_output(cmd,shell=True,cwd=ROOT,stderr=subprocess.STDOUT).decode().strip()

def loop():
  while True:
    con=sqlite3.connect(DB,timeout=30)
    rows=con.execute("select id,branch_name,title from dev_proposals where status='pr_created' and branch_name is not null and branch_name!=''").fetchall()
    for pid,branch,title in rows:
      try:
        out=run(f"gh pr list --head {branch} --json number")
        if not out:
          continue
        num=json.loads(out)[0]["number"]
        v=run(f"gh pr view {num} --json state,mergeable,mergedAt")
        j=json.loads(v)
        st=j.get("state")
        mg=j.get("mergeable")
        merged_at=j.get("mergedAt")
        if st=="MERGED" or merged_at:
          con.execute("update dev_proposals set status='merged' where id=?", (pid,))
          con.commit()
          print("merged",pid,title,flush=True)
        elif mg=="CONFLICTING":
          con.execute("update dev_proposals set status='conflict' where id=?", (pid,))
          con.commit()
          print("conflict",pid,title,flush=True)
      except Exception as e:
        print("watch_err",pid,branch,str(e),flush=True)
    con.close()
    time.sleep(20)

if __name__=="__main__":
  loop()
