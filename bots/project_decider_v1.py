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

def load_patterns(conn):
    rows = conn.execute(
        """
        select token, weight
        from decision_patterns
        order by abs(weight) desc, updated_at desc
        limit 200
        """
    ).fetchall()
    return [(str(r[0] or "").strip().lower(), float(r[1] or 0)) for r in rows if str(r[0] or "").strip()]

def score(title, desc, patterns):
    text = f"{title or ''} {desc or ''}".lower()
    priority = 0.0

    for k in KEYWORDS_EXECUTE:
        if k in text:
            priority += 1.0

    if "improve" in text or "optimize" in text:
        priority += 0.5

    matched = []
    for token, weight in patterns:
        if token and token in text:
            priority += weight
            matched.append((token, weight))

    if priority > 0.7:
        decision = "execute_now"
    elif priority > 0.4:
        decision = "backlog"
    else:
        decision = "archive"

    return decision, priority, matched

def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    patterns = load_patterns(conn)

    rows = conn.execute(
        """
        select id, title, description, status, project_decision
        from dev_proposals
        where status='approved'
          and coalesce(project_decision,'') in ('','backlog','archive','execute_now')
        order by id asc
        """
    ).fetchall()

    done = 0
    for r in rows:
        decision, priority, matched = score(r["title"], r["description"], patterns)
        conn.execute(
            """
            update dev_proposals
            set project_decision=?,
                priority=?
            where id=?
            """,
            (decision, priority, r["id"]),
        )
        if matched:
            conn.execute(
                """
                insert into dev_events(proposal_id,event_type,payload)
                values(
                  ?, 'decider_patterns_applied',
                  json_object(
                    'decision', ?,
                    'priority', ?,
                    'matched', ?,
                    'source', 'decision_patterns'
                  )
                )
                """,
                (
                    r["id"],
                    decision,
                    priority,
                    ",".join([f"{t}:{w}" for t, w in matched]),
                ),
            )
        done += 1

    conn.commit()
    conn.close()
    print(f"project_decider_done={done}", flush=True)

if __name__ == "__main__":
    main()
