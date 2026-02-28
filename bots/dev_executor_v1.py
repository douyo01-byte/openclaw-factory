import sqlite3
import subprocess
from bots.dev_schema_apply import apply as apply_dev_schema

DB_PATH = "data/openclaw.db"

def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd}\n{r.stdout}\n{r.stderr}")
    return r.stdout.strip()

def _run_ok(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0

def _has_remote(branch):
    return subprocess.run(["git","show-ref","--verify","--quiet",f"refs/remotes/origin/{branch}"]).returncode == 0

def _stash_push(tag):
    r = subprocess.run(["git","stash","push","-u","-m",tag], capture_output=True, text=True)
    out = (r.stdout or "") + (r.stderr or "")
    return r.returncode == 0 and "No local changes" not in out

def create_pr(proposal_id):
    apply_dev_schema(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT title, description FROM dev_proposals WHERE id = ?", (proposal_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False
    title, description = row
    branch = f"dev/proposal-{proposal_id}"

    stashed = _stash_push(f"dev_executor_{proposal_id}")

    _run_ok(["git","fetch","origin",branch])

    if _has_remote(branch):
        _run(["git","checkout","-B",branch,f"origin/{branch}"])
    else:
        _run(["git","checkout","-B",branch])

    _run(["git","add","."])

    has_changes = subprocess.run(["git","diff","--cached","--quiet"]).returncode != 0
    if has_changes:
        _run(["git","commit","-m",f"Dev Proposal #{proposal_id}"])
        r = subprocess.run(["git","push","--force-with-lease","origin",branch], capture_output=True, text=True)
        if r.returncode != 0:
            _run_ok(["git","fetch","origin",branch])
            if _has_remote(branch):
                _run(["git","rebase",f"origin/{branch}"])
            _run(["git","push","--force-with-lease","origin",branch])

    existing = _run(["gh","pr","list","--head",branch,"--state","all","--json","number"]).strip()
    if existing == "[]":
        _run(["gh","pr","create","--title",title,"--body",(description or "")])

    cur.execute("UPDATE dev_proposals SET status='pr_created' WHERE id=?", (proposal_id,))
    cur.execute("INSERT INTO dev_events (proposal_id,event_type,payload) VALUES (?,?,?)", (proposal_id,"pr_created","{}"))
    conn.commit()
    conn.close()

    if stashed:
        subprocess.run(["git","stash","pop"], capture_output=True, text=True)

    return True
