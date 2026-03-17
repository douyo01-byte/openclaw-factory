from __future__ import annotations
import os
import re
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

def slug(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9_-]", "", s)
    return s[:48].strip("-") or "final-executor"

def main():
    while True:
        try:
            con = conn()
            c = con.cursor()

            src = c.execute("""
                select
                  id,
                  coalesce(title,'') as title,
                  coalesce(description,'') as description,
                  cast(coalesce(priority,0) as integer) as priority,
                  coalesce(target_system,'') as target_system,
                  coalesce(improvement_type,'') as improvement_type,
                  coalesce(decision_note,'') as decision_note
                from dev_proposals
                where coalesce(source_ai,'')='ceo_final_executor_bridge_v1'
                  and coalesce(status,'')='new'
                  and coalesce(project_decision,'')='go'
                  and coalesce(decision_note,'') like '%final_executor_ready%'
                  and coalesce(decision_note,'') not like '%final_guard_promoted%'
                order by id asc
                limit 1
            """).fetchone()

            if not src:
                con.close()
                time.sleep(SLEEP)
                continue

            exists = c.execute("""
                select id
                from dev_proposals
                where coalesce(source_ai,'')='ceo_final_executor_guarded_promoter_v1'
                  and coalesce(decision_note,'') like ?
                order by id desc
                limit 1
            """, (f"%final_guard_from={src['id']}%",)).fetchone()

            if exists:
                note = src["decision_note"] or ""
                if "final_guard_promoted" not in note:
                    note = (note + " | final_guard_promoted").strip(" |")
                    c.execute("""
                        update dev_proposals
                        set decision_note=?
                        where id=?
                    """, (note, src["id"]))
                    con.commit()
                con.close()
                time.sleep(SLEEP)
                continue

            ts = datetime.now().strftime("%Y%m%d%H%M%S")
            branch = f"ceo-final-guard/{slug(src['target_system'])}-{src['id']}-{ts}"
            new_title = f"Executor最終投入候補 : {src['title']}"
            new_note = f"final_guard_from={src['id']} | {src['decision_note']}".strip(" |")

            c.execute("""
                insert into dev_proposals (
                  title, description, branch_name, status, risk_level,
                  created_at, processing, project_decision, dev_stage, pr_status,
                  pr_url, pr_number, spec_stage, spec, category, target_system,
                  improvement_type, quality_score, priority, score, result_type,
                  guard_status, guard_reason, decision_note, dev_attempts,
                  last_error, executed_at, source_ai, confidence, result_score,
                  result_note, notified_at, notified_msg_id, impact_score,
                  impact_level, impact_reason, impact_updated_at, target_policy
                ) values (
                  ?, ?, ?, 'new', 'medium',
                  CURRENT_TIMESTAMP, 0, 'go', '', '',
                  '', null, '', '', '', ?,
                  ?, 0, ?, 0, '',
                  '', '', ?, 0,
                  '', '', 'ceo_final_executor_guarded_promoter_v1', 0, 0,
                  '', '', '', 0,
                  '', '', '', ''
                )
            """, (
                new_title,
                src["description"],
                branch,
                src["target_system"],
                src["improvement_type"],
                max(int(src["priority"] or 0), 85),
                new_note,
            ))

            new_id = c.lastrowid

            src_note = src["decision_note"] or ""
            if "final_guard_promoted" not in src_note:
                src_note = (src_note + " | final_guard_promoted").strip(" |")

            c.execute("""
                update dev_proposals
                set decision_note=?
                where id=?
            """, (src_note, src["id"]))

            con.commit()
            con.close()
            print(f"{datetime.now().isoformat()} promoted={new_id}", flush=True)
        except Exception as e:
            print(f"ceo_final_executor_guarded_promoter_error: {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
