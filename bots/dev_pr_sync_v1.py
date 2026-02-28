import json
import sqlite3
import subprocess
from bots.dev_schema_apply import apply as apply_dev_schema

DB_PATH = "data/openclaw.db"

def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd}\n{r.stdout}\n{r.stderr}")
    return r.stdout.strip()

def sync():
    apply_dev_schema(DB_PATH)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    rows = cur.execute(
        "SELECT id, branch_name, status, pr_number, pr_url FROM dev_proposals WHERE status='pr_created' ORDER BY id"
    ).fetchall()

    for r in rows:
        pid = r["id"]
        branch = r["branch_name"]
        pr_number = r["pr_number"]
        pr_url = r["pr_url"]

        info = None
        try:
            j = _run(["gh","pr","view",str(pr_number) if pr_number else branch,"--json","number,url,state,mergedAt,closedAt","-q","{number:.number,url:.url,state:.state,mergedAt:.mergedAt,closedAt:.closedAt}"])
            info = json.loads(j)
        except Exception as e:
            cur.execute(
                "INSERT INTO dev_events (proposal_id,event_type,payload) VALUES (?,?,?)",
                (pid, "pr_sync_error", json.dumps({"error": str(e)[:500]})),
            )
            con.commit()
            continue

        new_number = info.get("number")
        new_url = info.get("url")
        state = info.get("state")
        merged_at = info.get("mergedAt")
        closed_at = info.get("closedAt")

        new_status = r["status"]
        if merged_at:
            new_status = "merged"
        elif state == "CLOSED" or closed_at:
            new_status = "closed"
        elif state == "MERGED":
            new_status = "merged"

        cur.execute(
            "UPDATE dev_proposals SET pr_number=COALESCE(pr_number,?), pr_url=COALESCE(pr_url,?), status=? WHERE id=?",
            (new_number, new_url, new_status, pid),
        )
        cur.execute(
            "INSERT INTO dev_events (proposal_id,event_type,payload) VALUES (?,?,?)",
            (pid, "pr_synced", json.dumps({"status": new_status, "number": new_number, "url": new_url})),
        )
        con.commit()

    con.close()
    return True

if __name__ == "__main__":
    sync()
