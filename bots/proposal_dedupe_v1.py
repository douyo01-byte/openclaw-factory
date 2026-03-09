import os
import sqlite3

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH", "data/openclaw.db")

def _norm_title(s: str) -> str:
    return " ".join((s or "").strip().lower().split())

def _revenue_body(title: str) -> str:
    t = (title or "").strip()
    if t.upper().startswith("REVENUE:"):
        t = t.split(":", 1)[1]
    return _norm_title(t)

def should_skip(conn, title: str, category: str, target_system: str, improvement_type: str, lookback: int = 120, signature_limit: int = 8):
    nt = _norm_title(title)
    sig = (category or "", target_system or "", improvement_type or "")

    dup = conn.execute("""
    select id
    from dev_proposals
    where lower(trim(title)) = lower(trim(?))
    order by id desc
    limit 1
    """, (title,)).fetchone()
    if dup:
        return True, "duplicate_title"

    rows = conn.execute("""
    select
      id,
      coalesce(title,'') as title,
      coalesce(category,'') as category,
      coalesce(target_system,'') as target_system,
      coalesce(improvement_type,'') as improvement_type
    from dev_proposals
    order by id desc
    limit ?
    """, (lookback,)).fetchall()

    same_sig = 0
    revenue_dup = False
    for r in rows:
        rsig = (r[2], r[3], r[4])
        if rsig == sig:
            same_sig += 1
        if category == "revenue":
            if _revenue_body(r[1]) == _revenue_body(title):
                revenue_dup = True

    if category == "revenue" and revenue_dup:
        return True, "duplicate_revenue_body"

    if same_sig >= signature_limit:
        return True, "duplicate_signature"

    return False, ""

def approved_idea_cap(conn, cap: int = 300) -> bool:
    n = conn.execute("""
    select count(*)
    from dev_proposals
    where status in ('approved','idea')
    """).fetchone()[0]
    return int(n or 0) >= cap
