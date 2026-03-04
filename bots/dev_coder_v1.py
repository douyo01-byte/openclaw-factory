import os,sqlite3,time,subprocess
DB=os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or "data/openclaw_real.db"
ROOT="/Users/doyopc/AI/openclaw-factory-daemon"
def run(cmd):
  subprocess.run(cmd,shell=True,cwd=ROOT)
def loop():
  while True:
    con=sqlite3.connect(DB,timeout=30)
    row=con.execute("select id,title from dev_proposals where status='spec' order by id asc limit 1").fetchone()
    if row:
      pid,title=row
      branch=f"auto/proposal-{pid}"
      fname=f"auto_feature_{pid}.txt"
      run(f"git checkout -b {branch}")
      run(f"echo '{title}' >> {fname}")
      run("git add .")
      run(f"git commit -m 'auto: proposal {pid}'")
      run(f"git push -u origin {branch}")
      con.execute("update dev_proposals set status='coded',branch_name=? where id=?",(branch,pid))
      con.commit()
      print("code_created",pid,title,flush=True)
    con.close()
    time.sleep(15)
if __name__=="__main__":
  loop()
