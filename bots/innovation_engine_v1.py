import os
import random
import sqlite3
try:
    from bots.proposal_dedupe_v1 import should_skip, approved_idea_cap
except ModuleNotFoundError:
    from proposal_dedupe_v1 import should_skip, approved_idea_cap

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or os.path.expanduser("/Users/doyopc/AI/openclaw-factory-daemon/data/openclaw_real.db")

ideas = [
    "Optimize query performance",
    "Improve log rotation",
    "Reduce executor latency",
    "Enhance PR watcher resilience",
    "Improve CI feedback parser",
    "Add auto retry for GitHub API",
    "Improve proposal ranking logic",
    "Improve executor stability guard",
    "Strengthen watcher recovery flow",
    "Reduce duplicate lifecycle events",
    "Improve learning result ordering",
    "Harden dashboard DB path handling",
    "Improve PR batching selection",
    "Stabilize mainstream proposal supply",
    "Improve backlog visibility in dashboard",
    "Reduce ceo_hub_events duplication",
    "Strengthen executor retry safety",
    "Improve open PR tracking accuracy",
    "Reduce watcher merge lag",
    "Harden automerge recovery flow",
    "Improve proposal supply diversity",
    "Improve batch anchor selection",
    "Reduce duplicate PR creation risk",
    "Improve lifecycle metrics accuracy",
    "Harden dashboard event summary",
    "Improve approved queue visibility",
    "Stabilize proposal generation loop",
    "Improve executor DB path safety",
    "Reduce supply loop dead time",
    "Improve core automation resilience",
    "Strengthen learning pipeline handoff",
    "Improve queue drain visibility",
]

CATEGORY = "automation"
TARGET_SYSTEM = "core"
IMPROVEMENT_TYPE = "stabilize"
QUALITY_SCORE = 70

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

if approved_idea_cap(conn, 300):
    print("skip=cap_reached")
    conn.close()
    raise SystemExit(0)

pool = []
for title in ideas:
    skip, reason = should_skip(conn, title, CATEGORY, TARGET_SYSTEM, IMPROVEMENT_TYPE)
    if skip:
        print(f"[dedupe] skip title={title} reason={reason}")
        continue
    pool.append(title)

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
""", (title, spec, spec, "approved", CATEGORY, TARGET_SYSTEM, IMPROVEMENT_TYPE, QUALITY_SCORE))

conn.commit()
print("inserted", title)
conn.close()
