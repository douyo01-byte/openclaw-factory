from __future__ import annotations
import os
import re
import time
import sqlite3
from datetime import datetime

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = 120

def norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"\s+", "", s)
    return s

def conn():
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    return con

def overlap_score(a: str, b: str) -> float:
    sa = set(norm(a))
    sb = set(norm(b))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / max(len(sa | sb), 1)

def classify(row, recent_rows):
    title = row["title"] or ""
    desc = row["description"] or ""
    target = row["target_system"] or ""
    imp = row["improvement_type"] or ""
    prio = int(row["priority"] or 0)

    duplicate_like = False
    best_overlap = 0.0
    dup_id = None

    for r in recent_rows:
        if r["id"] == row["id"]:
            continue
        score = max(
            overlap_score(title, r["title"] or ""),
            overlap_score(desc, r["description"] or "")
        )
        if score > best_overlap:
            best_overlap = score
            dup_id = r["id"]
        if score >= 0.72:
            duplicate_like = True

    burnin_hold = False
    if imp in ("ui_change", "wide_refactor", "product_expansion"):
        burnin_hold = True
    if "web" in norm(title) or "telegram" in norm(title):
        burnin_hold = True

    new_priority = prio
    notes = []

    if duplicate_like:
        new_priority = max(5, prio - 25)
        notes.append(f"duplicate_like_with={dup_id}")
        notes.append(f"overlap={best_overlap:.2f}")

    if target in ("router_tasks", "dev_pr_creator_v1", "dev_pr_watcher_v1"):
        new_priority = max(new_priority, 80)
        notes.append("mainline_reliability_relevant")

    if burnin_hold:
        new_priority = min(new_priority, 40)
        notes.append("burnin_hold_candidate")

    if not notes:
        notes.append("review_ok")

    if duplicate_like and burnin_hold:
        decision = "hold"
    elif duplicate_like:
        decision = "dedupe_check"
    elif burnin_hold:
        decision = "later"
    else:
        decision = "go"

    return new_priority, decision, " | ".join(notes)

def main():
    while True:
        try:
            con = conn()
            c = con.cursor()

            rows = c.execute("""
                select
                  id, coalesce(title,'') as title, coalesce(description,'') as description,
                  coalesce(source_ai,'') as source_ai,
                  coalesce(status,'') as status,
                  coalesce(target_system,'') as target_system,
                  coalesce(improvement_type,'') as improvement_type,
                  coalesce(priority,0) as priority,
                  coalesce(decision_note,'') as decision_note
                from dev_proposals
                where coalesce(source_ai,'')='ceo_problem_detector_v1'
                  and coalesce(status,'') in ('new','pending')
                  and coalesce(decision_note,'')=''
                order by id asc
                limit 20
            """).fetchall()

            recent = c.execute("""
                select
                  id, coalesce(title,'') as title, coalesce(description,'') as description
                from dev_proposals
                order by id desc
                limit 300
            """).fetchall()

            reviewed = 0
            for r in rows:
                new_priority, decision, note = classify(r, recent)
                c.execute("""
                    update dev_proposals
                    set priority=case when coalesce(priority,0) < ? then ? else priority end,
                        decision_note=?,
                        project_decision=?
                    where id=?
                """, (new_priority, note, decision, r["id"]))
                reviewed += 1

            con.commit()
            con.close()

            if reviewed:
                print(f"{datetime.now().isoformat()} reviewed={reviewed}", flush=True)

        except Exception as e:
            print(f"reviewer_error: {e}", flush=True)

        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
