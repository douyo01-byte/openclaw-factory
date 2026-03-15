import json
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
REPO = os.environ.get("GITHUB_REPO") or "douyo01-byte/openclaw-factory"
GH = os.environ.get("GH_BIN") or shutil.which("gh") or "/opt/homebrew/bin/gh"
ROOT = Path("/Users/doyopc/AI/openclaw-factory-daemon")
LOG = ROOT / "logs" / "auto_merge_cleaner_v1.out"
BATCH = int(os.environ.get("AUTO_MERGE_CLEANER_BATCH") or "3")

def log(msg):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(msg.rstrip() + "\n")
    print(msg, flush=True)

def sh(cmd):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stdout.strip())
    return r.stdout.strip()

def db():
    conn = sqlite3.connect(DB, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("pragma busy_timeout=30000")
    try:
        conn.execute("pragma journal_mode=WAL")
    except Exception:
        pass
    return conn

def pick_rows(conn):
    return conn.execute("""
    select
      id,
      coalesce(title,'') as title,
      coalesce(source_ai,'') as source_ai,
      coalesce(pr_number,'') as pr_number,
      coalesce(pr_url,'') as pr_url,
      coalesce(pr_status,'') as pr_status,
      coalesce(dev_stage,'') as dev_stage,
      coalesce(spec_stage,'') as spec_stage
    from dev_proposals
    where coalesce(pr_status,'')='open'
      and coalesce(pr_number,'')<>''
      and coalesce(pr_url,'')<>''
    order by id asc
    limit ?
    """, (BATCH,)).fetchall()

def pr_view(pr_number):
    out = sh([
        GH, "pr", "view", str(pr_number),
        "--repo", REPO,
        "--json",
        "number,state,isDraft,mergeStateStatus,reviewDecision,mergedAt,url"
    ])
    return json.loads(out)

def sync_db(conn, pid, pr):
    state = str(pr.get("state") or "").upper()
    merged_at = pr.get("mergedAt")
    if merged_at:
        conn.execute("update dev_proposals set pr_status='merged', status='merged', dev_stage='merged' where id=?", (pid,))
        conn.execute("update proposal_state set stage='merged', updated_at=datetime('now') where proposal_id=?", (pid,))
        return "merged"
    if state == "CLOSED":
        conn.execute("update dev_proposals set pr_status='closed', status='closed', dev_stage='closed' where id=?", (pid,))
        conn.execute("update proposal_state set stage='closed', updated_at=datetime('now') where proposal_id=?", (pid,))
        return "closed"
    conn.execute("update dev_proposals set pr_status='open', status='open', dev_stage='open' where id=?", (pid,))
    conn.execute("update proposal_state set stage='pr_created', updated_at=datetime('now') where proposal_id=? and coalesce(stage,'') not in ('merged','closed')", (pid,))
    return "open"

def queue_merge(pr_number):
    return sh([
        GH, "pr", "merge", str(pr_number),
        "--repo", REPO,
        "--auto",
        "--squash",
        "--delete-branch"
    ])

def main():
    conn = db()
    try:
        rows = pick_rows(conn)
        if not rows:
            log("rows=0")
            return

        done = 0
        for r in rows:
            pid = int(r["id"])
            prn = int(r["pr_number"])
            title = str(r["title"] or "")
            try:
                pr = pr_view(prn)
                status = sync_db(conn, pid, pr)
                conn.commit()

                if status != "open":
                    log(f"[AUTO_MERGE_CLEANER] pid={pid} pr={prn} status={status}")
                    continue

                if bool(pr.get("isDraft")):
                    log(f"[AUTO_MERGE_CLEANER] skip pid={pid} pr={prn} reason=draft")
                    continue

                review = str(pr.get("reviewDecision") or "")
                if review == "CHANGES_REQUESTED":
                    log(f"[AUTO_MERGE_CLEANER] skip pid={pid} pr={prn} reason=changes_requested")
                    continue

                merge_state = str(pr.get("mergeStateStatus") or "")
                if merge_state in ("DIRTY", "UNKNOWN"):
                    log(f"[AUTO_MERGE_CLEANER] skip pid={pid} pr={prn} reason={merge_state.lower() or 'unknown'}")
                    continue

                out = queue_merge(prn)
                log(f"[AUTO_MERGE_CLEANER] queued pid={pid} pr={prn} title={title} merge_state={merge_state} review={review} out={out}")
                done += 1
            except Exception as e:
                log(f"[AUTO_MERGE_CLEANER] error pid={pid} pr={prn} err={e}")

        log(f"done={done}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
