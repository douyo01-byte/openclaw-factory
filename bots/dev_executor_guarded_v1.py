import os,sqlite3,subprocess,datetime
from dev_executor_safe_v1 import main as run_one

DB=os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or "data/openclaw.db"
GH="/opt/homebrew/bin/gh"

MAX_INFLIGHT=int(os.environ.get("MAX_INFLIGHT_PRS","5"))

def now():
  return datetime.datetime.now(datetime.UTC).replace(microsecond=0).isoformat().replace("+00:00","Z")

def gh_graphql_remaining():
  try:
    out=subprocess.check_output([GH,"api","rate_limit","-q",".resources.graphql.remaining"],text=True).strip()
    return int(out)
  except Exception:
    return 999999

def main():
  con=sqlite3.connect(DB,timeout=30)
  inflight=con.execute("select count(*) from dev_proposals where status='pr_created'").fetchone()[0]
  con.close()

  if inflight >= MAX_INFLIGHT:
    print(now(),"skip: inflight",inflight,"/",MAX_INFLIGHT,flush=True)
    return 0

  # GraphQL枯渇時はPR作成を止める（watcher v2 は REST なので生きる）
  rem=gh_graphql_remaining()
  if rem < 50:
    print(now(),"skip: graphql_remaining",rem,flush=True)
    return 0

  return run_one()

if __name__=="__main__":
  raise SystemExit(main())
