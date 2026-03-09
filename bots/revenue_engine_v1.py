import datetime
import os
import random
import sqlite3
try:
    from bots.proposal_dedupe_v1 import should_skip, approved_idea_cap
except ModuleNotFoundError:
    from proposal_dedupe_v1 import should_skip, approved_idea_cap

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db")

ideas = [
    "Sell OpenClaw automation toolkit",
    "GitHub automation SaaS",
    "AI DevOps monitoring SaaS",
    "AI code optimization service",
    "Developer productivity SaaS",
]

CATEGORY = "revenue"
TARGET_SYSTEM = "product"
IMPROVEMENT_TYPE = "monetize"
QUALITY_SCORE = 78

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
for idea in ideas:
    title = f"REVENUE:{idea}"
    skip, reason = should_skip(conn, title, CATEGORY, TARGET_SYSTEM, IMPROVEMENT_TYPE)
    if skip:
        print(f"[dedupe] skip title={title} reason={reason}")
        continue
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
""", (title, spec, spec, "approved", CATEGORY, TARGET_SYSTEM, IMPROVEMENT_TYPE, QUALITY_SCORE))

c.execute("""
insert into ceo_hub_events(event_type,title,body,created_at)
values(?,?,?,?)
""", ("revenue", "AI Revenue Idea", idea, datetime.datetime.utcnow()))

conn.commit()
print("inserted", title)
conn.close()
