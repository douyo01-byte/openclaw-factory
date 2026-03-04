import os,sqlite3,subprocess,time,datetime,traceback

DB=os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or "data/openclaw.db"
REPO=os.environ.get("GITHUB_REPO","douyo01-byte/openclaw-factory")
GH="/opt/homebrew/bin/gh"

def now():
  return datetime.datetime.now(datetime.UTC).replace(microsecond=0).isoformat().replace("+00:00","Z")

def sh(args):
  return subprocess.check_output(args,text=True).strip()

def pr_info(n:int):
  # REST: merged_at が入れば MERGED
  # state は open/closed
  j=sh([GH,"api",f"repos/{REPO}/pulls/{n}","-q",".merged_at + \"|\" + .state"])
  merged_at,state=j.split("|",1)
  merged = bool(merged_at and merged_at!="null")
  return merged,state

def loop():
  while True:
    try:
      con=sqlite3.connect(DB,timeout=30)
      rows=con.execute("""
select id, pr_number, coalesce(pr_status,'')
from dev_proposals
where status='pr_created' and pr_number is not null and pr_number!=0
order by id asc
limit 50
""").fetchall()
      touched=0
      for pid,pr,st in rows:
        try:
          merged,state=pr_info(int(pr))
        except Exception:
          time.sleep(1)
          continue
        if merged:
          con.execute("""
update dev_proposals
set status='merged', dev_stage='merged', pr_status='merged'
where id=?
""",(pid,))
          con.commit(); touched+=1
        else:
          s=state.lower()
          if s!=st:
            con.execute("update dev_proposals set pr_status=? where id=?", (s,pid))
            con.commit(); touched+=1
      print(now(),"checked",len(rows),"touched",touched,flush=True)
      con.close()
    except Exception:
      print(now(),"ERR",flush=True)
      traceback.print_exc()
    time.sleep(5)

if __name__=="__main__":
  loop()
