import os,sqlite3,time,subprocess
DB=os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or "data/openclaw_real.db"
ROOT="/Users/doyopc/AI/openclaw-factory-daemon"
def run(cmd):
  subprocess.run(cmd,shell=True,cwd=ROOT)
def loop():
  while True:
    con=sqlite3.connect(DB,timeout=30)
    row=con.execute("select id,branch_name,title from dev_proposals where status='coded' order by id asc limit 1").fetchone()
    if row:
      pid,branch,title=row
      cmd=f"gh pr create --title 'auto: {title}' --body 'auto generated from proposal {pid}' --base main --head {branch}"
      run(cmd)
      con.execute("update dev_proposals set status='pr_created' where id=?", (pid,))
      con.commit()
      print("pr_created",pid,title,flush=True)
    con.close()
    time.sleep(15)
if __name__=="__main__":
  loop()
