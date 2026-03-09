import os, sqlite3, random

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

def build_spec(title):
    return f"""Goal:
Implement proposal: {title}

Scope:
- change only minimal related files
- preserve current Lv6/Lv7 core loop
- avoid broad refactor
- keep PR small and reviewable

Acceptance:
- code compiles
- no regression in current pipeline
- change is limited to target concern
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
    dup = c.execute("""
    select 1 from dev_proposals
    where lower(title)=lower(?)
    order by id desc limit 1
    """, (idea,)).fetchone()
    if not dup:
        pool.append(idea)

if not pool:
    print("skip=no_new_idea")
    conn.close()
    raise SystemExit(0)

title = random.choice(pool)
spec = build_spec(title)

c.execute("""
insert into dev_proposals(
  title,description,spec,status,spec_stage,project_decision,guard_status,guard_reason,
  created_at,category,target_system,improvement_type,quality_score
) values(
  ?,?,?,?,'refined','execute_now','safe','bootstrap_spec',datetime('now'),?,?,?,?
)
""", (title, spec, spec, "approved", "automation", "core", "stabilize", 70))

conn.commit()
print("inserted", title)
conn.close()
