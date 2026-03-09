import os, sqlite3, subprocess, random

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db")
REPO = "/Users/doyopc/AI/openclaw-factory"
checks = [
    "Improve error handling",
    "Refactor duplicated logic",
    "Optimize database queries",
    "Improve logging coverage",
    "Reduce API latency",
    "Improve retry logic",
]

def build_spec(title):
    return f"""Goal:
Implement targeted code improvement: {title}

Scope:
- edit only directly related file(s)
- keep PR minimal
- preserve current behavior except target fix
- avoid repo-wide refactor

Acceptance:
- affected code compiles
- targeted improvement is visible
- current pipeline keeps working
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

files = subprocess.check_output(["git", "-C", REPO, "ls-files"], text=True).splitlines()
random.shuffle(files)

title = None
for target in files[:300]:
    cand = f"{random.choice(checks)} in {target}"
    dup = c.execute("""
    select 1 from dev_proposals
    where lower(title)=lower(?)
    order by id desc limit 1
    """, (cand,)).fetchone()
    if not dup:
        title = cand
        break

if not title:
    print("skip=no_new_code_review")
    conn.close()
    raise SystemExit(0)

spec = build_spec(title)

c.execute("""
insert into dev_proposals(
  title,description,spec,status,spec_stage,project_decision,guard_status,guard_reason,
  created_at,category,target_system,improvement_type,quality_score
) values(
  ?,?,?,?,'refined','execute_now','safe','bootstrap_spec',datetime('now'),?,?,?,?
)
""", (title, spec, spec, "approved", "automation", "codebase", "refactor", 72))

conn.commit()
print("inserted", title)
conn.close()
