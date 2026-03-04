import os,sqlite3,time,datetime,subprocess

DB=os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or "data/openclaw.db"
GH="/opt/homebrew/bin/gh"
MAX_INFLIGHT=int(os.environ.get("MAX_INFLIGHT_PRS","5"))

def now():
  return datetime.datetime.now(datetime.UTC).replace(microsecond=0).isoformat().replace("+00:00","Z")

def graphql_remaining():
  try:
    out=subprocess.check_output([GH,"api","rate_limit","-q",".resources.graphql.remaining"],text=True).strip()
    return int(out)
  except Exception:
    return 999999

while True:
  try:
    con=sqlite3.connect(DB,timeout=30)

    inflight=con.execute(
      "select count(*) from dev_proposals where status='pr_created'"
    ).fetchone()[0]

    if inflight >= MAX_INFLIGHT:
      print(now(),"skip inflight",inflight,flush=True)
      con.close()
      time.sleep(5)
      continue

    if graphql_remaining() < 50:
      print(now(),"skip graphql",flush=True)
      con.close()
      time.sleep(10)
      continue

    rows=con.execute("""
select id from dev_proposals
where status in ('pending','proposed')
order by id asc
limit 10
""").fetchall()

    touched=0

    for (pid,) in rows:
      con.execute("""
update dev_proposals
set status='approved',
dev_stage='approved',
decided_by='auto',
decided_at=datetime('now')
where id=?
""",(pid,))
      con.commit()
      touched+=1

    con.close()
    print(now(),"auto_approved",touched,flush=True)

  except Exception as e:
    print(now(),"ERR",e,flush=True)

  time.sleep(5)
