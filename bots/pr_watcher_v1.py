import os,sqlite3,time,subprocess,json
DB=os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or "data/openclaw_real.db"
ROOT="/Users/doyopc/AI/openclaw-factory-daemon"
def run(cmd):
  return subprocess.check_output(cmd,shell=True,cwd=ROOT).decode().strip()
def loop():
  while True:
    con=sqlite3.connect(DB,timeout=30)
    rows=con.execute("select id,branch_name,title from dev_proposals where status='pr_created'").fetchall()
    for pid,branch,title in rows:
      try:
        out=run(f"gh pr list --head {branch} --json number,state")
        if out:
          data=json.loads(out)[0]
          num=data["number"]
          state=data["state"]
          if state=="OPEN":
            run(f"gh pr merge {num} --merge --auto")
            con.execute("update dev_proposals set status='merged' where id=?", (pid,))
            con.commit()
            print("merged",pid,title,flush=True)
      except:
        pass
    con.close()
    time.sleep(20)
if __name__=="__main__":
  loop()
