import os, re, sqlite3, subprocess, json

DB=os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH","data/openclaw.db")
REPO=os.environ.get("GITHUB_REPO","")

def sh(cmd):
  r=subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
  if r.returncode!=0:
    raise SystemExit(r.stdout.strip())
  return r.stdout.strip()

def ensure_clean():
  if sh(["git","status","--porcelain"]).strip():
    raise SystemExit("git dirty")

def append_readme(par):
  p="README.md"
  try:
    s=open(p,"r",encoding="utf-8").read()
  except FileNotFoundError:
    s=""
  if par in s:
    return False
  s = (s.rstrip()+"\n\n"+par.strip()+"\n")
  open(p,"w",encoding="utf-8").write(s)
  return True

def run():
  if not REPO:
    raise SystemExit("GITHUB_REPO required")
  conn=sqlite3.connect(DB)
  conn.row_factory=sqlite3.Row

  rows=conn.execute(
    "select id,title,description,branch_name from dev_proposals "
    "where status='approved' and (pr_number is null or pr_number='') "
    "order by id asc limit 20"
  ).fetchall()
  if not rows:
    return

  ensure_clean()
  sh(["git","fetch","origin","main"])
  sh(["git","checkout","main"])
  sh(["git","reset","--hard","origin/main"])

  for r in rows:
    pid=int(r["id"])
    title=(r["title"] or f"Proposal {pid}").strip()
    body=(r["description"] or "").strip()
    branch=(r["branch_name"] or f"dev/proposal-{pid}").strip()

    if sh(["git","branch","--list",branch]).strip()=="":
      sh(["git","checkout","-b",branch])
    else:
      sh(["git","checkout",branch])
      sh(["git","reset","--hard","origin/main"])

    par="提案→PR→自動マージ: Telegramで「提案: <内容>」を送る → 自動でdev_proposalsに登録 → 「承認します #<id>」でapproved → PR作成・通知 → マージ後にstatus=mergedへ更新。"
    changed=append_readme(par)
    if not changed:
      sh(["git","checkout","main"])
      continue

    sh(["git","add","README.md"])
    sh(["git","commit","-m",f"docs: proposal flow ({pid})"])
    sh(["git","push","-u","origin",branch])

    j=sh(["gh","pr","create","-R",REPO,"-H",branch,"-B","main","-t",title,"-b",body])
    data=json.loads(j)
    conn.execute(
      "update dev_proposals set pr_number=?, pr_url=?, pr_status='pr_created' where id=?",
      (int(data["number"]), data["url"], pid)
    )
    conn.commit()

    sh(["git","checkout","main"])
    sh(["git","reset","--hard","origin/main"])

if __name__=="__main__":
  run()
