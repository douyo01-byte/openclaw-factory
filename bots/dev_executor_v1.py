import sqlite3
import subprocess
from bots.dev_schema_apply import apply as apply_dev_schema

DB_PATH = "data/openclaw.db"

def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd}\n{r.stdout}\n{r.stderr}")
    return r.stdout.strip()

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
    _run(["git", "checkout", "-b", branch])
    _run(["git", "add", "."])
    _run(["git", "commit", "-m", f"Dev Proposal #{proposal_id}"])
    _run(["git", "push", "origin", branch])
    _run(["gh", "pr", "create", "--title", title, "--body", (description or "")])
    cur.execute("UPDATE dev_proposals SET status = 'pr_created' WHERE id = ?", (proposal_id,))
    cur.execute("INSERT INTO dev_events (proposal_id, event_type, payload) VALUES (?, ?, ?)", (proposal_id, "pr_created", "{}"))
    conn.commit()
    conn.close()
    return True
