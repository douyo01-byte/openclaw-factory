from __future__ import annotations
import os
import sqlite3
import time
from datetime import datetime

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = 180

def conn():
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    return con

def eff_priority(row):
    p = int(row["priority"] or 0)
    note = row["decision_note"] or ""
    if "priority_fixed_85" in note:
        p = max(p, 85)
    return p

def main():
    while True:
        try:
            con = conn()
            c = con.cursor()

            row = c.execute("""
                select
                  id,
                  coalesce(title,'') as title,
                  coalesce(description,'') as description,
                  coalesce(source_ai,'') as source_ai,
                  coalesce(status,'') as status,
                  cast(coalesce(priority,0) as integer) as priority,
                  coalesce(project_decision,'') as project_decision,
                  coalesce(decision_note,'') as decision_note,
                  coalesce(target_system,'') as target_system,
                  coalesce(improvement_type,'') as improvement_type,
                  coalesce(branch_name,'') as branch_name
                from dev_proposals
                where coalesce(source_ai,'')='ceo_mainline_promoter_v1'
                  and coalesce(status,'')='new'
                  and coalesce(project_decision,'')='go'
                  and coalesce(decision_note,'') like '%selected_for_execution%'
                  and coalesce(decision_note,'') like '%executor_ready%'
                  and coalesce(decision_note,'') not like '%guard_promoted_to_executor%'
                order by id asc
                limit 1
            """).fetchone()

            promoted = 0

            if row is not None:
                p = eff_priority(row)
                if p >= 80:
                    title = f"Executor投入: {row['title']}"
                    desc = row["description"] or row["title"] or ""
                    note = row["decision_note"] or ""
                    branch = row["branch_name"] or f"ceo-guarded-{row['id']}"
                    target = row["target_system"] or ""
                    imp = row["improvement_type"] or ""

                    c.execute("""
                        insert into dev_proposals
                        (
                          title, description, branch_name, status,
                          risk_level, project_decision, dev_stage, pr_status,
                          spec_stage, spec, category, target_system, improvement_type,
                          priority, score, result_type, guard_status, guard_reason,
                          decision_note, dev_attempts, last_error, executed_at,
                          source_ai, confidence, result_score, result_note,
                          notified_at, notified_msg_id, impact_score, impact_level,
                          impact_reason, impact_updated_at, target_policy, created_at
                        )
                        values (
                          ?, ?, ?, 'new',
                          'medium', 'go', '', '',
                          '', '', '', ?, ?,
                          ?, 0, '', '', '',
                          ?, 0, '', '',
                          'ceo_executor_guarded_promoter_v1', 0, 0, '',
                          '', '', 0, '', '', '', '', datetime('now')
                        )
                    """, (
                        title,
                        desc,
                        branch,
                        target,
                        imp,
                        p,
                        f"guard_promoted_from={row['id']} | {note}",
                    ))

                    c.execute("""
                        update dev_proposals
                        set decision_note = coalesce(decision_note,'') || ' | guard_promoted_to_executor'
                        where id=?
                    """, (row["id"],))
                    promoted = 1

            con.commit()
            con.close()

            if promoted:
                print(f"{datetime.now().isoformat()} promoted={promoted}", flush=True)
        except Exception as e:
            print(f"guarded_promoter_error: {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
