from __future__ import annotations
import os
import sqlite3
import time

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = int(os.environ.get("TARGET_POLICY_GUARD_SLEEP", "20"))

ARCHIVE_KEYS = [
    "auto_merge_v1",
    "auto_pr_v1",
    "openai_smoke",
    "browser_smoke",
    "ops_brain_v1",
    "ops_brain_v2",
    "ops_brain_v3",
    "explain_orchestrator_v1",
    "meeting_hn_v1",
    "report_orchestrator_v1",
    "market_brain_v1",
    "innovation_engine_v1",
    "revenue_engine_v1",
    "project_brain_v4",
    "company_dashboard_v1",
    "ceo_help_v1",
    "auto_plan_v1",
]
PARK_KEYS = [
    "chat_research_v1",
]

def connect():
    con = sqlite3.connect(DB, timeout=30)
    con.execute("PRAGMA busy_timeout=30000")
    return con

def ensure_column():
    con = connect()
    try:
        cols = [r[1] for r in con.execute("PRAGMA table_info(dev_proposals)")]
        if "target_policy" not in cols:
            con.execute("ALTER TABLE dev_proposals ADD COLUMN target_policy TEXT DEFAULT ''")
            con.commit()
    finally:
        con.close()

def classify_title(title: str) -> str:
    t = (title or "").lower()
    if any(k in t for k in ARCHIVE_KEYS):
        return "archived_or_parked"
    if any(k in t for k in PARK_KEYS):
        return "parked"
    return ""

def run_once():
    con = connect()
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute("""
            select id, title, coalesce(status,'') as status, coalesce(dev_stage,'') as dev_stage,
                   coalesce(pr_status,'') as pr_status, coalesce(target_policy,'') as target_policy
            from dev_proposals
            order by id desc
            limit 500
        """).fetchall()

        classified = 0
        blocked = 0

        for r in rows:
            tp = r["target_policy"] or classify_title(r["title"])
            if tp and (r["target_policy"] or "") != tp:
                con.execute("update dev_proposals set target_policy=? where id=?", (tp, r["id"]))
                classified += 1

            if tp and r["status"] in ("pending", "approved") and r["dev_stage"] not in ("merged", "closed", "blocked_target_policy"):
                con.execute("""
                    update dev_proposals
                    set status='approved',
                        dev_stage='blocked_target_policy',
                        guard_status='blocked_target_policy',
                        guard_reason='target blocked by active bot policy',
                        target_policy=?
                    where id=?
                """, (tp, r["id"]))
                blocked += 1

        con.commit()
        print(f"[target_policy_guard] classified={classified} blocked={blocked}", flush=True)
    finally:
        con.close()

def main():
    ensure_column()
    while True:
        run_once()
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
