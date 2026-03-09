import os, sqlite3, random, datetime

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db")
ideas = [
    "Optimize query performance",
    "Improve log rotation",
    "Reduce executor latency",
    "Enhance PR watcher resilience",
    "Improve CI feedback parser",
    "Add auto retry for GitHub API",
    "Improve proposal ranking logic",
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
    dup = c.execute("""
    select 1
    from dev_proposals
    where lower(title)=lower(?)
    order by id desc
    limit 1
    """, (idea,)).fetchone()
    if not dup:
        pool.append(idea)

if not pool:
    print("skip=no_new_idea")
    conn.close()
    raise SystemExit(0)

idea = random.choice(pool)
c.execute("""
insert into dev_proposals(title,status,created_at,category,target_system,improvement_type,quality_score)
values(?,?,datetime('now'),?,?,?,?)
""", (idea, "approved", "automation", "core", "stabilize", 70))
conn.commit()
print("inserted", idea)
conn.close()
