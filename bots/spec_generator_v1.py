import os,sqlite3,time
DB=os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or "data/openclaw_real.db"
def loop():
  while True:
    con=sqlite3.connect(DB,timeout=30)
    row=con.execute("select id,title from dev_proposals where status='idea' order by id asc limit 1").fetchone()
    if row:
      pid,title=row
      spec="SPEC:"+title
      con.execute("update dev_proposals set status='spec',description=? where id=?",(spec,pid))
      con.commit()
      print("spec_created",pid,title,flush=True)
    con.close()
    time.sleep(10)
if __name__=="__main__":
  loop()
