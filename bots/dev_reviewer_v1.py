from __future__ import annotations
import argparse, json, os, re, subprocess, sys

def sh(cmd, check=True):
  r=subprocess.run(cmd, text=True, capture_output=True)
  if check and r.returncode!=0:
    sys.stderr.write(r.stdout)
    sys.stderr.write(r.stderr)
    raise SystemExit(r.returncode)
  return r.stdout.strip()

def ghj(args):
  out=sh(["gh"]+args+["--json","number,title,url,headRefName,baseRefName,isDraft,state"], check=True)
  return json.loads(out) if out else []

def list_prs(repo, base, limit):
  q=["pr","list","--repo",repo,"--base",base,"--state","open","--limit",str(limit)]
  out=sh(["gh"]+q+["--json","number,title,url,headRefName,baseRefName,isDraft,state"], check=True)
  return json.loads(out) if out else []

def pr_diff(repo, n):
  return sh(["gh","pr","diff",str(n),"--repo",repo], check=True)

def pr_files(repo, n):
  out=sh(["gh","pr","view",str(n),"--repo",repo,"--json","files"], check=True)
  j=json.loads(out) if out else {}
  return [f.get("path","") for f in j.get("files",[])]

def pr_view(repo, n):
  out=sh(["gh","pr","view",str(n),"--repo",repo,"--json","title,url,headRefName,baseRefName,isDraft,state,author"], check=True)
  return json.loads(out) if out else {}

def analyze(diff_text, files):
  issues=[]
  if len(diff_text)>200000:
    issues.append("diffが大きすぎます。分割してください。")
  if any(p.endswith((".lock",".png",".jpg",".jpeg",".webp",".pdf",".zip")) for p in files):
    issues.append("バイナリ/ロック/画像等が含まれています。意図を明記してください。")
  if re.search(r"\bTODO\b", diff_text):
    issues.append("TODOが残っています。削除か理由の記載が必要です。")
  if re.search(r"\bprint\(", diff_text):
    issues.append("print\(\)が差分に含まれています。必要ならloggingへ置換してください。")
  if re.search(r"\bDEBUG\b", diff_text):
    issues.append("DEBUGが残っています。削除してください。")
  if "py_compile" in diff_text:
    pass
  if "requests" in diff_text and "requirements" not in diff_text.lower():
    issues.append("requests追加の可能性があります。依存管理を確認してください。")
  return issues

def build_comment(meta, issues):
  lines=[]
  lines.append("自動レビュー結果")
  lines.append(f"- base: {meta.get('baseRefName')}")
  lines.append(f"- head: {meta.get('headRefName')}")
  if not issues:
    lines.append("")
    lines.append("指摘なし。次工程（修正不要ならmerge準備）へ進めます。")
    return "\n".join(lines), True
  lines.append("")
  lines.append("要対応:")
  for i,s in enumerate(issues,1):
    lines.append(f"{i}. {s}")
  lines.append("")
  lines.append("対応後、このPRに再度レビュー依頼してください。")
  return "\n".join(lines), False

def comment_pr(repo, n, body):
  sh(["gh","pr","comment",str(n),"--repo",repo,"-b",body], check=True)

def main():
  ap=argparse.ArgumentParser()
  ap.add_argument("--repo", default=os.environ.get("GITHUB_REPO",""))
  ap.add_argument("--base", default=os.environ.get("REVIEW_BASE","main"))
  ap.add_argument("--limit", type=int, default=int(os.environ.get("REVIEW_LIMIT","20")))
  ap.add_argument("--pr", type=int, default=0)
  ap.add_argument("--dry", action="store_true")
  a=ap.parse_args()

  repo=a.repo.strip()
  if not repo:
    repo=sh(["gh","repo","view","--json","nameWithOwner","-q",".nameWithOwner"], check=True)

  prs=[]
  if a.pr:
    prs=[{"number":a.pr}]
  else:
    prs=list_prs(repo, a.base, a.limit)

  for p in prs:
    n=int(p["number"])
    meta=pr_view(repo, n)
    if meta.get("isDraft"):
      continue
    d=pr_diff(repo, n)
    files=pr_files(repo, n)
    issues=analyze(d, files)
    body, ok=build_comment(meta, issues)
    if a.dry:
      continue
    comment_pr(repo, n, body)

if __name__=="__main__":
  main()
