import os, sqlite3, time

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
PR_RATE_LIMIT = 10

def pr_rate_ok(conn):
    cur = conn.cursor()
    cur.execute("""
        select count(*)
        from dev_proposals
        where coalesce(pr_status,'')='open'
           or coalesce(status,'')='open'
           or coalesce(dev_stage,'')='open'
    """)
    n = cur.fetchone()[0]
    return n < PR_RATE_LIMIT

def judge(title, branch_name):
    t = (title or "").lower()
    b = (branch_name or "").lower()
    if not branch_name:
        return "hold", "missing_branch"
    if "danger" in t or "drop" in t or "delete" in t:
        return "hold", "danger_keyword"
    if "security" in t:
        return "safe", "ok"
    if "executor" in t:
        return "safe", "ok"
    if "watcher" in t:
        return "safe", "ok"
    if "learning" in t:
        return "safe", "ok"
    if "parallel" in t:
        return "safe", "ok"
    if "cache" in t:
        return "safe", "ok"
    if "ai automation tool" in t:
        return "safe", "ok"
    if b.startswith("dev/"):
        return "safe", "ok"
    return "hold", "needs_review"

def run_once():
    conn = sqlite3.connect(DB, timeout=30)
    cur = conn.cursor()
    print("=== Executor Guard v3 ===", flush=True)

    if not pr_rate_ok(conn):
        print("PR rate limit reached", flush=True)
        conn.close()
        return

    cur.execute("""
        select id, title, branch_name
        from dev_proposals
        where coalesce(status,'')='approved'
          and coalesce(project_decision,'')='execute_now'
          and coalesce(guard_status,'pending')='pending'
        order by id asc
        limit 20
    """)
    rows = cur.fetchall()

    for pid, title, branch_name in rows:
        status, reason = judge(title, branch_name)
        cur.execute("""
            update dev_proposals
            set guard_status=?,
                guard_reason=?
            where id=?
        """, (status, reason, pid))
        print((pid, title, branch_name, status, reason), flush=True)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    while True:
        run_once()
        time.sleep(60)
