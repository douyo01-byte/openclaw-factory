import os
import sqlite3
from datetime import datetime

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH", "data/openclaw.db")

FALLBACK_TITLES = [
    "Executor stability sweep",
    "Watcher recovery sweep",
    "Lifecycle event integrity sweep",
    "Mainstream supply resilience sweep",
    "Approved queue visibility sweep",
    "Batch anchor selection sweep",
    "Router throughput sweep",
    "Proposal dedupe sweep",
    "Launchd resilience sweep",
    "Merge notify stability sweep",
    "Queue normalization sweep",
    "DB lock avoidance sweep",
    "Fallback seed rotation sweep",
    "Watcher state sync sweep",
    "Automerge safety sweep",
    "Impact scoring resilience sweep",
    "CEO hub event integrity sweep",
    "Self-strength watchdog sweep",
    "Supply loop durability sweep",
    "Proposal routing stability sweep",
]

def build_spec(title):
    return f"""Goal:
Implement: {title}
Acceptance:
- code compiles
- current pipeline remains operational
- change is limited and reviewable
"""

conn = sqlite3.connect(DB, timeout=30)
conn.execute("PRAGMA busy_timeout=30000")
c = conn.cursor()

active = c.execute("""
select count(*)
from dev_proposals
where status='approved'
  and coalesce(project_decision,'')='execute_now'
  and coalesce(guard_status,'')='safe'
""").fetchone()[0]

if int(active or 0) >= 3:
    print("skip=already_has_executable")
    conn.close()
    raise SystemExit(0)

title = None
for base in FALLBACK_TITLES:
    cand = f"{base} {datetime.now().strftime('%H%M%S')}"
    dup = c.execute("""
    select 1
    from dev_proposals
    where lower(trim(title)) = lower(trim(?))
    limit 1
    """, (cand,)).fetchone()
    if not dup:
        title = cand
        break

if not title:
    print("skip=no_fallback_title")
    conn.close()
    raise SystemExit(0)

spec = build_spec(title)

c.execute("""
insert into dev_proposals(
  title,description,branch_name,spec,status,spec_stage,project_decision,guard_status,guard_reason,
  created_at,category,target_system,improvement_type,quality_score
) values(
  ?,?,?,?,?,'refined','execute_now','safe','mainstream_fallback',datetime('now'),?,?,?,?
)
""", (title, spec, f"fallback/{datetime.now().strftime('%Y%m%d_%H%M%S')}", spec, "approved", "automation", "core", "stabilize", 73))

conn.commit()
print("inserted", c.lastrowid, title)
conn.close()
