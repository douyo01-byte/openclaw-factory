import os,sqlite3,subprocess,time,datetime,traceback

DB=os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or "data/openclaw.db"
GH="/opt/homebrew/bin/gh"

def now():
  return datetime.datetime.now(datetime.UTC).replace(microsecond=0).isoformat().replace("+00:00","Z")

def try_automerge(pr:int)->bool:
  # 成功すれば 0
  subprocess.check_call([GH,"pr","merge",str(pr),"--merge","--auto","--delete-branch","--admin"])
  return True

def loop():
  while True:
    try:
      con=sqlite3.connect(DB,timeout=30)
      rows=con.execute("""
select id, pr_number, coalesce(pr_status,'')
from dev_proposals
where status='pr_created'
  and pr_number is not null and pr_number!=0
  and coalesce(pr_status,'') not in ('auto_merge_set','merged')
order by id asc
limit 30
""").fetchall()
      touched=0
      for pid,pr,st in rows:
        try:
          ok=try_automerge(int(pr))
          if ok:
            con.execute("update dev_proposals set pr_status='auto_merge_set' where id=?", (pid,))
            con.commit(); touched+=1
        except Exception:
          # 既にMERGED/Closedや権限系は watcher に任せる。ここで無限にerrorにしない。
          time.sleep(1)
          continue
      print(now(),"automerge_checked",len(rows),"touched",touched,flush=True)
      con.close()
    except Exception:
      print(now(),"ERR",flush=True)
      traceback.print_exc()
    time.sleep(5)

if __name__=="__main__":
  loop()
