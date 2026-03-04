import os,sqlite3,subprocess,time,datetime,json,traceback,re,tempfile

DB=os.environ.get("DB_PATH","data/openclaw.db")
GH=os.environ.get("GH","/opt/homebrew/bin/gh")
REPO_DIR=os.environ.get("REPO_DIR", os.path.expanduser("~/AI/openclaw-factory"))
MAX_INFLIGHT=int(os.environ.get("MAX_INFLIGHT","3"))

def now():
  return datetime.datetime.now(datetime.UTC).replace(microsecond=0).isoformat().replace("+00:00","Z")

def sh(args, cwd=None):
  subprocess.check_call(args, cwd=cwd)

def out(args, cwd=None):
  return subprocess.check_output(args, cwd=cwd, text=True).strip()

def gh_graphql_remaining():
  try:
    v=out([GH,"api","rate_limit","-q",".resources.graphql.remaining"])
    return int(v)
  except Exception:
    return 999999

def pick_one(con):
  r=con.execute("""
select id,title,coalesce(description,''),branch_name
from dev_proposals
where status='approved'
order by id asc
limit 1
""").fetchone()
  return r

def mark(con, pid, status=None, dev_stage=None, pr_status=None, err=None):
  cols=[]
  vals=[]
  if status is not None:
    cols.append("status=?"); vals.append(status)
  if dev_stage is not None:
    cols.append("dev_stage=?"); vals.append(dev_stage)
  if pr_status is not None:
    cols.append("pr_status=?"); vals.append(pr_status)
  if err is not None:
    cols.append("dev_last_error=?"); vals.append(err)
  if not cols:
    return
  vals.append(pid)
  con.execute("update dev_proposals set "+",".join(cols)+" where id=?", vals)
  con.commit()

def ensure_clean_repo():
  sh(["git","checkout","-f","main"], cwd=REPO_DIR)
  sh(["git","fetch","-p","origin","main"], cwd=REPO_DIR)
  sh(["git","reset","--hard","origin/main"], cwd=REPO_DIR)
  sh(["git","clean","-fd"], cwd=REPO_DIR)

def branch_exists_local(b):
  try:
    out(["git","rev-parse","--verify",b], cwd=REPO_DIR)
    return True
  except Exception:
    return False

def delete_branch_if_exists(b):
  sh(["git","checkout","-f","main"], cwd=REPO_DIR)
  try: sh(["git","branch","-D",b], cwd=REPO_DIR)
  except Exception: pass
  try: sh(["git","push","origin","--delete",b], cwd=REPO_DIR)
  except Exception: pass

def openai_chat(prompt):
  # 既存の環境で OPENAI_API_KEY を使って動く前提。ここは最小実装。
  # 使っているSDK差異を避けるため、curlで叩く。
  key=os.environ.get("OPENAI_API_KEY","").strip()
  if not key:
    raise RuntimeError("OPENAI_API_KEY missing")
  model=os.environ.get("OPENAI_MODEL","gpt-4.1-mini")
  import urllib.request
  import urllib.error
  url="https://api.openai.com/v1/chat/completions"
  body=json.dumps({
    "model": model,
    "messages": [
      {"role":"system","content":"You are a senior software engineer. Output ONLY a unified diff patch. No prose."},
      {"role":"user","content": prompt}
    ],
    "temperature": 0.2
  }).encode("utf-8")
  req=urllib.request.Request(url, data=body, method="POST")
  req.add_header("Content-Type","application/json")
  req.add_header("Authorization", f"Bearer {key}")
  with urllib.request.urlopen(req, timeout=60) as r:
    data=json.loads(r.read().decode("utf-8"))
  return data["choices"][0]["message"]["content"]

def build_prompt(pid, title, desc):
  return f"""
Repo: openclaw-factory (Python).
Task title: {title}
Task description: {desc}

Constraints:
- Make a SMALL, SAFE change (<= 150 lines).
- Prefer adding a new file or small edit.
- Must keep project runnable.
- Provide ONLY a unified diff (git apply compatible).
- If unsure about exact paths, add a new file under bots/ or oclibs/ with minimal dependencies.

Goal:
Implement the requested change.
"""

def extract_diff(txt):
  txt=txt.strip()
  if "diff --git" not in txt:
    raise RuntimeError("no diff --git in model output")
  return txt

def apply_patch(diff_text):
  with tempfile.NamedTemporaryFile("w", delete=False) as f:
    f.write(diff_text)
    p=f.name
  try:
    sh(["git","apply","--whitespace=fix",p], cwd=REPO_DIR)
  finally:
    try: os.unlink(p)
    except Exception: pass

def py_compile_all():
  py=os.path.join(REPO_DIR,".venv","bin","python")
  if not os.path.exists(py):
    py="python3"
  sh([py,"-m","py_compile"] + list(find_py_files()), cwd=REPO_DIR)

def find_py_files():
  for root,dirs,files in os.walk(REPO_DIR):
    if "/.git/" in root: continue
    if "/.venv/" in root: continue
    for fn in files:
      if fn.endswith(".py"):
        yield os.path.join(root,fn)

def create_pr(b, pid, title):
  sh(["git","checkout","-b",b], cwd=REPO_DIR)
  sh(["git","add","-A"], cwd=REPO_DIR)
  sh(["git","commit","-m",f"dev: proposal #{pid} codegen"], cwd=REPO_DIR)
  sh(["git","push","-u","origin",b], cwd=REPO_DIR)
  url=out([GH,"pr","create","--title",f"[dev] proposal #{pid}","--body","auto codegen","--base","main","--head",b], cwd=REPO_DIR).splitlines()[-1].strip()
  pr=int(url.rstrip("/").split("/")[-1])
  return pr,url

def main():
  rem=gh_graphql_remaining()
  if rem < 50:
    print(now(),"skip: graphql_remaining",rem,flush=True)
    return 0

  con=sqlite3.connect(DB,timeout=30)
  inflight=con.execute("select count(*) from dev_proposals where status='pr_created'").fetchone()[0]
  if inflight >= MAX_INFLIGHT:
    con.close()
    print(now(),"skip: inflight",inflight,"/",MAX_INFLIGHT,flush=True)
    return 0

  row=pick_one(con)
  if not row:
    con.close()
    print(now(),"no approved",flush=True)
    return 0

  pid,title,desc,branch_name=row
  mark(con,pid, status="processing", dev_stage="codegen")
  con.close()

  b=f"auto-p{pid}"
  try:
    ensure_clean_repo()
    if branch_exists_local(b):
      delete_branch_if_exists(b)
      ensure_clean_repo()

    prompt=build_prompt(pid,title,desc)
    diff=extract_diff(openai_chat(prompt))
    apply_patch(diff)
    py_compile_all()

    pr, url=create_pr(b,pid,title)

    con=sqlite3.connect(DB,timeout=30)
    con.execute("""
update dev_proposals
set status='pr_created', pr_number=?, pr_url=?, pr_status='open', dev_stage='pr_created'
where id=?
""",(pr,url,pid))
    con.commit()
    con.close()
    print(now(),"ok pid",pid,"pr",pr,flush=True)
    return 0
  except Exception as e:
    err=f"{type(e).__name__}: {e}"
    try:
      con=sqlite3.connect(DB,timeout=30)
      mark(con,pid, status="hold", pr_status="error", dev_stage="error", err=err)
      con.close()
    except Exception:
      pass
    print(now(),"ERR pid",pid,err,flush=True)
    traceback.print_exc()
    return 1

if __name__=="__main__":
  raise SystemExit(main())
