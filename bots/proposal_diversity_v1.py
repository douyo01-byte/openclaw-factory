import sqlite3

RECENT_TITLE_WINDOW = 80
RECENT_CATEGORY_WINDOW = 6
RECENT_SOURCE_WINDOW = 6

def ensure_kv(conn):
    conn.execute("create table if not exists kv(k text primary key, v text, updated_at text default (datetime('now')))")

def norm(s):
    return (s or "").strip().lower()

def recent_titles(conn, limit=RECENT_TITLE_WINDOW):
    rows = conn.execute("""
        select coalesce(title,'')
        from dev_proposals
        order by id desc
        limit ?
    """, (limit,)).fetchall()
    return [norm(r[0]) for r in rows]

def recent_categories(conn, limit=RECENT_CATEGORY_WINDOW):
    rows = conn.execute("""
        select coalesce(category,'')
        from dev_proposals
        order by id desc
        limit ?
    """, (limit,)).fetchall()
    return [norm(r[0]) for r in rows]

def recent_sources(conn, limit=RECENT_SOURCE_WINDOW):
    rows = conn.execute("""
        select coalesce(source_ai, brain_type, '')
        from dev_proposals
        order by id desc
        limit ?
    """, (limit,)).fetchall()
    return [norm(r[0]) for r in rows]

def backlog_count(conn):
    return conn.execute("""
        select count(*)
        from dev_proposals
        where coalesce(status,'')='approved'
    """).fetchone()[0]

def title_exists_recent(conn, title, limit=RECENT_TITLE_WINDOW):
    t = norm(title)
    return t in set(recent_titles(conn, limit))

def category_streak(conn, category, streak=2):
    cats = recent_categories(conn, streak)
    if len(cats) < streak:
        return False
    c = norm(category)
    return all(x == c for x in cats)

def source_streak(conn, source_ai, streak=2):
    srcs = recent_sources(conn, streak)
    if len(srcs) < streak:
        return False
    s = norm(source_ai)
    return all(x == s for x in srcs)

def can_insert(conn, title, category, source_ai):
    if title_exists_recent(conn, title):
        return False, "dup_title_recent"
    if category_streak(conn, category, 2):
        return False, "same_category_streak"
    if source_streak(conn, source_ai, 2):
        return False, "same_source_streak"
    return True, "ok"

def insert_proposal(conn, title, description, branch_name, spec, source_ai, brain_type, confidence, category):
    conn.execute("""
        insert into dev_proposals
        (title,description,branch_name,status,spec,source_ai,brain_type,confidence,category,created_at)
        values (?,?,?,?,?,?,?,?,?,datetime('now'))
    """, (title, description, branch_name, "approved", spec, source_ai, brain_type, confidence, category))

def pick_first_allowed(conn, ideas, source_ai):
    for idea in ideas:
        title, description, branch_name, category, spec, confidence = idea
        ok, reason = can_insert(conn, title, category, source_ai)
        if ok:
            return idea, reason
    return None, "no_allowed_candidate"
