import os, sqlite3, random, datetime

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db")
ideas = [
    "Sell OpenClaw automation toolkit",
    "GitHub automation SaaS",
    "AI DevOps monitoring SaaS",
    "AI code optimization service",
    "Developer productivity SaaS",
]

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
    title = f"REVENUE:{idea}"
    dup = c.execute("""
    select 1
    from dev_proposals
    where lower(title)=lower(?)
    order by id desc
    limit 1
    """, (title,)).fetchone()
    if not dup:
        pool.append(idea)

if not pool:
    print("skip=no_new_revenue")
    conn.close()
    raise SystemExit(0)

idea = random.choice(pool)
title = f"REVENUE:{idea}"

c.execute("""
insert into dev_proposals(title,status,created_at,category,target_system,improvement_type,quality_score)
values(?,?,datetime('now'),?,?,?,?)
""", (title, "approved", "revenue", "product", "monetize", 78))

c.execute("""
insert into ceo_hub_events(event_type,title,body,created_at)
values(?,?,?,?)
""", ("revenue", "AI Revenue Idea", idea, datetime.datetime.utcnow()))

conn.commit()
print("inserted", title)
conn.close()
