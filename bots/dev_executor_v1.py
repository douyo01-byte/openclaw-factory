from __future__ import annotations
from datetime import datetime, timezone
import json
import os
import re
import sqlite3
import subprocess

DB_PATH = os.environ.get("OCLAW_DB_PATH", "/Users/doyopc/AI/openclaw-factory/data/openclaw.db")
BASE_BRANCH = "main"
REPO = "/Users/doyopc/AI/openclaw-factory"
KAI_LOG = os.path.join(REPO, "logs", "kai_actions.log")
MAX_OPEN_PRS = int(os.environ.get("EXECUTOR_MAX_OPEN_PRS", "5"))
MIN_PR_INTERVAL_SEC = int(os.environ.get("EXECUTOR_MIN_PR_INTERVAL_SEC", "30"))
BATCH_SIZE = int(os.environ.get("EXECUTOR_BATCH_SIZE", "3"))

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def sh(args, capture=False):
    env = dict(os.environ)
    env["HOME"] = "/Users/doyopc"
    env["PATH"] = "/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    if capture:
        p = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=REPO,
            env=env,
        )
        return p.stdout.strip()
    subprocess.run(args, cwd=REPO, env=env, check=True)

def kai(conn, pid, event, **kw):
    os.makedirs(os.path.dirname(KAI_LOG), exist_ok=True)
    payload = {"ts": now(), "proposal_id": pid, "event": event, **kw}
    with open(KAI_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    conn.execute(
        "INSERT INTO dev_events (proposal_id,event_type,payload) VALUES (?,?,?)",
        (pid, event, json.dumps(payload, ensure_ascii=False)),
    )

def ensure_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS kv(
            k TEXT PRIMARY KEY,
            v TEXT NOT NULL,
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

def kv_get(conn, k):
    r = conn.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
    return r[0] if r else None

def kv_set(conn, k, v):
    conn.execute("""
        INSERT INTO kv(k,v,updated_at) VALUES(?,?,datetime('now'))
        ON CONFLICT(k) DO UPDATE SET v=excluded.v, updated_at=datetime('now')
    """, (k, str(v)))

def open_pr_count(conn):
    r = conn.execute("""
        SELECT count(*)
        FROM dev_proposals
        WHERE coalesce(pr_status,'')='open'
           OR coalesce(status,'')='open'
           OR coalesce(dev_stage,'')='open'
    """).fetchone()
    return int(r[0] or 0)

def interval_ok(conn):
    last_ts = kv_get(conn, "executor_last_pr_created_at")
    if not last_ts:
        return True
    try:
        last_dt = datetime.strptime(last_ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return True
    delta = (datetime.now(timezone.utc) - last_dt).total_seconds()
    return delta >= MIN_PR_INTERVAL_SEC

def extract_pr_number(pr_url: str):
    if not pr_url:
        return None
    m = re.search(r"/pull/(\d+)", pr_url)
    return int(m.group(1)) if m else None

def pick_proposals(conn):
    return conn.execute("""
        SELECT id,title,description,branch_name,pr_number,pr_url,dev_stage,dev_attempts,spec
        FROM dev_proposals
        WHERE status='approved'
          AND coalesce(project_decision,'')='execute_now'
          AND coalesce(guard_status,'')='safe'
          AND coalesce(spec,'')!=''
          AND (dev_stage IS NULL OR dev_stage='' OR dev_stage='approved')
        ORDER BY id ASC
        LIMIT ?
    """, (BATCH_SIZE,)).fetchall()

def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    ensure_tables(conn)

    n_open = open_pr_count(conn)
    if n_open >= MAX_OPEN_PRS:
        print(f"pr_rate_skip=open_prs:{n_open}/{MAX_OPEN_PRS}", flush=True)
        return 0

    if not interval_ok(conn):
        print(f"pr_rate_skip=interval:{MIN_PR_INTERVAL_SEC}s", flush=True)
        return 0

    rows = pick_proposals(conn)
    if not rows:
        print("no executable proposals", flush=True)
        return 0

    pids = [int(r["id"]) for r in rows]
    first_pid = pids[0]
    last_pid = pids[-1]
    branch = f"dev/batch-{first_pid}-{last_pid}"
    batch_title = f"batch improvements {first_pid}-{last_pid}"

    sh(["/usr/bin/git", "checkout", BASE_BRANCH])
    kai(conn, first_pid, "git_base", base=BASE_BRANCH)
    sh(["/usr/bin/git", "fetch", "origin", BASE_BRANCH])
    sh(["/usr/bin/git", "reset", "--hard", "origin/" + BASE_BRANCH])
    sh(["/usr/bin/git", "clean", "-fd"])

    exists = sh(["/usr/bin/git", "ls-remote", "--heads", "origin", branch], capture=True)
    if exists:
        sh(["/usr/bin/git", "checkout", branch])
        sh(["/usr/bin/git", "fetch", "origin", branch])
        sh(["/usr/bin/git", "reset", "--hard", "origin/" + branch])
        sh(["/usr/bin/git", "clean", "-fd"])
    else:
        sh(["/usr/bin/git", "checkout", "-B", branch])

    os.makedirs(os.path.join(REPO, "dev_autogen"), exist_ok=True)

    body_parts = []
    for row in rows:
        pid = int(row["id"])
        title = (row["title"] or f"proposal {pid}").strip()
        description = row["description"] or row["spec"] or ""
        kai(conn, pid, "picked", branch_name=branch, title=title)
        fpath = os.path.join(REPO, "dev_autogen", f"p{pid}.txt")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(f"id={pid}\n")
            f.write(f"title={title}\n")
            f.write(f"batch={first_pid}-{last_pid}\n")
            f.write(f"ts={now()}\n\n")
            f.write(description[:4000])
        body_parts.append(f"proposal_id: {pid}\ntitle: {title}\n\n{description[:1200]}")

    sh(["/usr/bin/git", "add", "dev_autogen"])
    sh(["/usr/bin/git", "commit", "-m", f"dev: batch proposals #{first_pid}-#{last_pid} bootstrap PR"])
    sh(["/usr/bin/git", "push", "-u", "origin", branch])
    kai(conn, first_pid, "git_push", branch=branch)

    prj = sh(
        [
            "/opt/homebrew/bin/gh",
            "pr",
            "create",
            "--base",
            BASE_BRANCH,
            "--head",
            branch,
            "--title",
            f"[dev] {batch_title}",
            "--body",
            "\n\n---\n\n".join(body_parts),
        ],
        capture=True,
    )

    pr_url = prj.strip().splitlines()[-1].strip()
    pr_num = extract_pr_number(pr_url)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS ceo_hub_events(
          id integer primary key,
          event_type text,
          title text,
          body text,
          proposal_id integer,
          pr_url text,
          created_at text default (datetime('now')),
          sent_at text
        )
    """)

    for row in rows:
        pid = int(row["id"])
        title = (row["title"] or f"proposal {pid}").strip()
        conn.execute("""
            UPDATE dev_proposals
            SET status='pr_created',
                dev_stage='pr_created',
                pr_number=COALESCE(?,pr_number),
                pr_url=COALESCE(?,pr_url),
                branch_name=?,
                dev_attempts=COALESCE(dev_attempts,0)+1
            WHERE id=?
        """, (pr_num, pr_url, branch, pid))
        conn.execute("""
            INSERT INTO ceo_hub_events(event_type,title,body,proposal_id,pr_url)
            VALUES(?,?,?,?,?)
        """, (
            "pr_created",
            f"PR作 成 : {title}",
            f"branch: {branch} batch={first_pid}-{last_pid}",
            pid,
            pr_url,
        ))

    kv_set(conn, "executor_last_pr_created_at", now())
    conn.commit()

    payload = {
        "proposal_ids": pids,
        "branch": branch,
        "pr_number": pr_num,
        "pr_url": pr_url,
        "batch_size": len(pids),
        "max_open_prs": MAX_OPEN_PRS,
        "min_interval_sec": MIN_PR_INTERVAL_SEC,
    }
    print(json.dumps(payload, ensure_ascii=False), flush=True)

    conn.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
