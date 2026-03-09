import os
import random
import sqlite3
import subprocess
try:
    from bots.proposal_dedupe_v1 import should_skip, approved_idea_cap
except ModuleNotFoundError:
    from proposal_dedupe_v1 import should_skip, approved_idea_cap

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or os.path.expanduser("~/AI/openclaw-factory//Users/doyopc/AI/openclaw-factory-daemon/data/openclaw_real.db")
REPO = "/Users/doyopc/AI/openclaw-factory"

checks = [
    "Improve error handling",
    "Refactor duplicated logic",
    "Optimize database queries",
    "Improve logging coverage",
    "Reduce API latency",
    "Improve retry logic",
]

CATEGORY = "automation"
TARGET_SYSTEM = "codebase"
IMPROVEMENT_TYPE = "refactor"
QUALITY_SCORE = 72

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

files = subprocess.check_output(["git", "-C", REPO, "ls-files"], text=True).splitlines()
random.shuffle(files)

proposal = None
for target in files[:300]:
    cand = f"{random.choice(checks)} in {target}"
    skip, reason = should_skip(conn, cand, CATEGORY, TARGET_SYSTEM, IMPROVEMENT_TYPE)
    if skip:
        print(f"[dedupe] skip title={cand} reason={reason}")
        continue
    proposal = cand
    break

if not proposal:
    print("skip=no_new_code_review")
    conn.close()
    raise SystemExit(0)

spec = build_spec(proposal)

c.execute("""
insert into dev_proposals(
  title,description,spec,status,spec_stage,project_decision,guard_status,guard_reason,
  created_at,category,target_system,improvement_type,quality_score
) values(
  ?,?,?,?,'refined','execute_now','safe','bootstrap_spec',datetime('now'),?,?,?,?
)
""", (proposal, spec, spec, "approved", CATEGORY, TARGET_SYSTEM, IMPROVEMENT_TYPE, QUALITY_SCORE))

conn.commit()
print("inserted", proposal)
conn.close()
