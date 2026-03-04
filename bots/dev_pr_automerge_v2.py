import os,sqlite3,subprocess,time,datetime,traceback

DB=os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or "data/openclaw.db"
GH="/opt/homebrew/bin/gh"

def now():
  return datetime.datetime.now(datetime.UTC).replace(microsecond=0).isoformat().replace("+00:00","Z")

def run(cmd):
  return subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)

def pr_state(pr):
  r=run([GH,"pr","view",str(pr),"--json","state","--jq",".state"])
  if r.returncode!=0:
    return None
  return r.stdout.strip()

def try_automerge(pr):
  st=pr_state(pr)
  if st!="OPEN":
    return False
  r=run([GH,"pr","merge",str(pr),"--auto","--delete-branch"])
  return r.returncode==0

def loop():
  while True:
    try:
      con=sqlite3.connect(DB,timeout=30)
      rows=con.execute("""
select id, pr_number
from dev_proposals
where status='pr_created'
and pr_number is not null
and pr_number!=0
and coalesce(pr_status,'') not in ('auto_merge_set','merged')
order by id asc
limit 30
""").fetchall()
      touched=0
      for pid,pr in rows:
        try:
          if try_automerge(int(pr)):
            con.execute("update dev_proposals set pr_status='auto_merge_set' where id=?", (pid,))
            con.commit()
            touched+=1
          else:
            st=pr_state(pr)
            if st and st!="OPEN":
              con.execute("update dev_proposals set pr_status='merged', status='merged' where id=?", (pid,))
              con.commit()
        except Exception:
          time.sleep(1)
      print(now(),"automerge_checked",len(rows),"touched",touched,flush=True)
      con.close()
    except Exception:
      print(now(),"ERR",flush=True)
      traceback.print_exc()
    time.sleep(5)

if __name__=="__main__":
  loop()
