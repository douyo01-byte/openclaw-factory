import os,sqlite3,time,random
DB=os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or "data/openclaw_real.db"
ideas=[
"Add memory usage debug command",
"Add disk usage debug command",
"Add health check endpoint",
"Add environment dump debug command"
]
def loop():
  while True:
    con=sqlite3.connect(DB,timeout=30)
    n=con.execute("select count(*) from dev_proposals where status in ('idea','approved','pr_created')").fetchone()[0]
    if n<5:
      title=random.choice(ideas)
      con.execute("insert into dev_proposals(title,status,dev_stage) values(?,?,?)",(title,"idea","idea"))
      con.commit()
      print("idea_created",title,flush=True)
    con.close()
    time.sleep(20)
if __name__=="__main__":
  loop()
