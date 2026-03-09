import os, sqlite3, random, datetime

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db")
ideas = [
    "Sell OpenClaw automation toolkit",
    "GitHub automation SaaS",
    "AI DevOps monitoring SaaS",
    "AI code optimization service",
    "Developer productivity SaaS",
]

def build_spec(title):
    return f"""Goal:
Implement revenue-oriented proposal: {title}

Scope:
- small, isolated implementation only
- keep current automation stable
- no broad architectural rewrite
- prepare auto-PR compatible change

Acceptance:
- executable by current dev_executor
- minimal PR footprint
- no breakage to Lv6/Lv7 loop
"""

conn = sqlite3.connect(DB, timeout=30)
conn.execute("PRAGMA busy_timeout=30000")
c = conn.cursor()

cap = c.execute("""
select count(*)
from dev_proposals
where status in ('approved','idea')
""").fetchone()[0]
if cap >= 300:
    print("skip=cap")
    conn.close()
    raise SystemExit(0)

pool = []
for idea in ideas:
    t = f"REVENUE:{idea}"
    dup = c.execute("""
    select 1 from dev_proposals
    where lower(title)=lower(?)
    order by id desc limit 1
    """, (t,)).fetchone()
    if not dup:
        pool.append(idea)

if not pool:
    print("skip=no_new_revenue")
    conn.close()
    raise SystemExit(0)

idea = random.choice(pool)
title = f"REVENUE:{idea}"
spec = build_spec(title)

c.execute("""
insert into dev_proposals(
  title,description,spec,status,spec_stage,project_decision,guard_status,guard_reason,
  created_at,category,target_system,improvement_type,quality_score
) values(
  ?,?,?,?,'refined','execute_now','safe','bootstrap_spec',datetime('now'),?,?,?,?
)
""", (title, spec, spec, "approved", "revenue", "product", "monetize", 78))

c.execute("""
insert into ceo_hub_events(event_type,title,body,created_at)
values(?,?,?,?)
""", ("revenue", "AI Revenue Idea", idea, datetime.datetime.utcnow()))

conn.commit()
print("inserted", title)
conn.close()
