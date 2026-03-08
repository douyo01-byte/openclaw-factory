import sqlite3

CATEGORY_ORDER = [
    "infrastructure",
    "performance",
    "learning",
    "automation",
    "reliability",
    "telemetry",
    "cost",
    "security",
    "dev_experience",
    "AI capability",
]

def backlog_count(conn):
    return conn.execute("""
        select count(*)
        from dev_proposals
        where coalesce(status,'')='approved'
    """).fetchone()[0]

def _recent_rows(conn, limit=30):
    return conn.execute("""
        select
          id,
          coalesce(title,'') as title,
          coalesce(category,'') as category,
          coalesce(source_ai,brain_type,'') as src
        from dev_proposals
        order by id desc
        limit ?
    """, (limit,)).fetchall()

def _recent_titles(conn, limit=80):
    return {
        (r[0] or "").strip().lower()
        for r in conn.execute("""
            select coalesce(title,'')
            from dev_proposals
            order by id desc
            limit ?
        """, (limit,))
    }

def _recent_categories(conn, limit=6):
    return [
        (r[0] or "").strip()
        for r in conn.execute("""
            select coalesce(category,'')
            from dev_proposals
            order by id desc
            limit ?
        """, (limit,))
    ]

def _same_source_recent(conn, source_ai, limit=6):
    return [
        (r[0] or "").strip()
        for r in conn.execute("""
            select coalesce(category,'')
            from dev_proposals
            where coalesce(source_ai,brain_type,'')=?
            order by id desc
            limit ?
        """, (source_ai, limit))
    ]

def can_insert(conn, title, category, source_ai):
    t = (title or "").strip().lower()
    c = (category or "").strip()

    if not t:
        return False, "empty_title"
    if not c:
        return False, "empty_category"

    recent_titles = _recent_titles(conn, 120)
    if t in recent_titles:
        return False, "duplicate_title_recent"

    recent_categories = _recent_categories(conn, 3)
    if len(recent_categories) >= 2 and recent_categories[0] == c and recent_categories[1] == c:
        return False, "recent_category_streak"

    same_source_recent = _same_source_recent(conn, source_ai, 2)
    if len(same_source_recent) >= 2 and same_source_recent[0] == c and same_source_recent[1] == c:
        return False, "same_source_category_streak"

    return True, "ok"

def pick_first_allowed(conn, ideas, source_ai):
    last_reason = "no_candidates"
    for item in ideas:
        title, desc, branch, category, spec, conf = item
        ok, reason = can_insert(conn, title, category, source_ai)
        if ok:
            return item, "ok"
        last_reason = reason
    return None, last_reason

def insert_proposal(conn, title, description, branch_name, spec, source_ai, brain_type, confidence, category):
    conn.execute("""
        insert into dev_proposals
        (title,description,branch_name,status,spec,source_ai,brain_type,confidence,category,created_at)
        values (?,?,?,?,?,?,?,?,?,datetime('now'))
    """, (
        title,
        description,
        branch_name,
        "approved",
        spec,
        source_ai,
        brain_type,
        confidence,
        category,
    ))
