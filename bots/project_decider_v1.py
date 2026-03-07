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
    s = 0.0
    for k in KEYWORDS_EXECUTE:
        if k in text:
            s += 1.5
    if "improve" in text or "optimize" in text:
        s += 0.5
    if s >= 2.0:
        return "execute_now", s
    if s >= 0.5:
        return "backlog", s
    return "archive", s

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
