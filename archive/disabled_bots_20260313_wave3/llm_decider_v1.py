import sqlite3, os, time

DB = os.environ["DB_PATH"]

EXEC_NOW_KEYWORDS = [
    "watcher", "logging", "log", "executor", "retry", "backup",
    "database", "telegram", "resilience", "rotation", "latency",
    "monitor", "ai log analytics", "productivity dashboard"
]

def decide(row):
    title = (row["title"] or "").lower()
    brain = (row["brain_type"] or "").lower()
    target = (row["target_system"] or "").lower()
    improve = (row["improvement_type"] or "").lower()
    priority = float(row["priority"] or 0)
    has_spec = bool((row["spec"] or "").strip())

    if priority >= 5:
        return "execute_now", "high priority proposal"

    if has_spec and any(k in title for k in EXEC_NOW_KEYWORDS):
        return "execute_now", "keyword matched and spec ready"

    if has_spec and target in ("watcher", "executor", "database", "telegram"):
        return "execute_now", "core target with spec"

    if has_spec and improve in ("stabilize", "monitor", "optimize", "refactor"):
        return "execute_now", "implementation-ready improvement"

    if has_spec and (title.startswith("revenue:") or brain in ("revenue", "business")):
        return "execute_now", "business/revenue proposal with spec"

    if priority <= 0 and not has_spec:
        return "archive", "low signal without spec"

    if has_spec:
        return "backlog", "kept with spec but lower priority"

    return "backlog", "default keep decision"

while True:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
    select id,title,brain_type,priority,
           coalesce(target_system,'') as target_system,
           coalesce(improvement_type,'') as improvement_type,
           coalesce(spec,'') as spec
    from dev_proposals
    where status='approved'
    order by priority desc,id desc
    limit 200
    """).fetchall()

    for r in rows:
        d, n = decide(r)
        conn.execute("""
        update dev_proposals
        set project_decision=?,
            decision_note=?
        where id=?
        """, (d, n, r["id"]))

    conn.commit()

    top = conn.execute("""
    select id,title,priority,project_decision,decision_note
    from dev_proposals
    where status='approved'
    order by priority desc,id desc
    limit 20
    """).fetchall()

    print("\n=== LLM Decider v2 ===\n", flush=True)
    for t in top:
        print(tuple(t), flush=True)

    conn.close()
    time.sleep(60)
