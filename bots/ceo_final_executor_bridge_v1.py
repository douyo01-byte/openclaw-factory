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

def branch_name_from_id(row_id: int) -> str:
    return f"ceo-final-executor-{row_id}"

def main():
    while True:
        try:
            con = conn()
            c = con.cursor()
            rows = c.execute("""
                select
                  id,
                  coalesce(title,'') as title,
                  coalesce(description,'') as description,
                  cast(coalesce(priority,0) as integer) as priority,
                  coalesce(target_system,'') as target_system,
                  coalesce(improvement_type,'') as improvement_type,
                  coalesce(decision_note,'') as decision_note
                from dev_proposals
                where coalesce(source_ai,'')='ceo_guarded_mainline_promoter_v1'
                  and coalesce(status,'')='new'
                  and coalesce(project_decision,'')='selected_now'
                  and coalesce(decision_note,'') like '%final_executor_selected%'
                  and coalesce(decision_note,'') not like '%final_executor_bridged%'
                order by id asc
                limit 10
            """).fetchall()

            bridged = 0
            for r in rows:
                src_id = int(r["id"])
                title = f"Executor最終投入: {r['title']}"
                desc = r["description"] or r["title"]
                note = r["decision_note"] or ""
                priority = int(r["priority"] or 0)

                c.execute("""
                    insert into dev_proposals (
                      title, description, branch_name, status, risk_level,
                      created_at, processing, project_decision, dev_stage, pr_status,
                      pr_url, spec_stage, spec, category, target_system,
                      improvement_type, priority, score, result_type, guard_status,
                      guard_reason, decision_note, dev_attempts, last_error,
                      executed_at, source_ai, confidence, result_score, result_note,
                      notified_at, notified_msg_id, impact_score, impact_level,
                      impact_reason, impact_updated_at, target_policy
                    ) values (
                      ?, ?, ?, 'new', 'medium',
                      datetime('now'), 0, 'go', '', '',
                      '', '', '', '', ?,
                      ?, ?, 0, '', '',
                      '', ?, 0, '',
                      '', 'ceo_final_executor_bridge_v1', 0, 0, '',
                      '', '', 0, '',
                      '', '', ''
                    )
                """, (
                    title,
                    desc,
                    branch_name_from_id(src_id),
                    r["target_system"],
                    r["improvement_type"],
                    priority,
                    f"final_executor_from={src_id} | {note}"
                ))

                new_note = note
                if "final_executor_bridged" not in new_note:
                    new_note = (new_note + " | final_executor_bridged").strip(" |")
                c.execute("""
                    update dev_proposals
                    set decision_note=?
                    where id=?
                """, (new_note, src_id))
                bridged += 1

            con.commit()
            con.close()

            if bridged:
                print(f"{datetime.now().isoformat()} bridged={bridged}", flush=True)
        except Exception as e:
            print(f"final_executor_bridge_error: {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
