import os
import sqlite3

DB = os.environ.get("DB_PATH", "data/openclaw.db")

KEYWORDS_EXECUTE = [
    "safety",
    "security",
    "merge",
    "executor",
    "automation",
    "pipeline",
    "logging",
]

def score(title: str, desc: str) -> tuple[str, float]:
    text = f"{title} {desc}".lower()
    priority = 0.0
    for k in KEYWORDS_EXECUTE:
        if k in text:
            priority += 1.0
    if "improve" in text or "optimize" in text:
        priority += 0.5
    if priority > 0.7:
        decision = "execute_now"
    elif priority > 0.4:
        decision = "backlog"
    else:
        decision = "archive"
    return decision, priority

def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        select id,title,description,status,project_decision
        from dev_proposals
        where status='approved'
          and coalesce(project_decision,'') in ('','backlog','archive')
        order by id asc
        """
    ).fetchall()
    done = 0
    for r in rows:
        decision, priority = score(r["title"] or "", r["description"] or "")
        conn.execute(
            """
            update dev_proposals
            set project_decision=?,
                priority=coalesce(priority,0) + ?
            where id=?
            """,
            (decision, priority, r["id"]),
        )
        done += 1
    conn.commit()
    conn.close()
    print(f"project_decider_done={done}", flush=True)

if __name__ == "__main__":
    main()
