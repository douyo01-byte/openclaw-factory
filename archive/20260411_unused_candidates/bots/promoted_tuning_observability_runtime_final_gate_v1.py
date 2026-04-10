#!/usr/bin/env python3
import os
import sqlite3

DB = os.environ["DB_PATH"]

con = sqlite3.connect(DB)
try:
    con.execute("""
    create table if not exists decider_tuning_observability_runtime_final_gate (
      proposal_id integer primary key,
      gate_status text not null,
      gate_reason text not null,
      checked_at text not null default (datetime('now')),
      source text not null
    )
    """)
    rows = con.execute("""
    select dp.id
    from dev_proposals dp
    left join decider_tuning_observability_runtime_plan p on p.proposal_id = dp.id
    left join decider_tuning_observability_runtime_applied a on a.proposal_id = dp.id
    where coalesce(dp.guard_status,'')='observability_runtime_review_only'
      and coalesce(dp.guard_reason,'')='human_review_observability_runtime_applied'
    order by dp.id
    """).fetchall()

    n = 0
    for (proposal_id,) in rows:
        plan_action = con.execute("""
        select coalesce(plan_action,'')
        from decider_tuning_observability_runtime_plan
        where proposal_id=?
        """, (proposal_id,)).fetchone()
        applied_row = con.execute("""
        select 1
        from decider_tuning_observability_runtime_applied
        where proposal_id=?
        """, (proposal_id,)).fetchone()

        if applied_row and plan_action and plan_action[0] == "ready_for_observability_runtime":
            gate_status = "open_for_observability_runtime_rollout"
            gate_reason = "runtime_applied_and_planned"
        else:
            gate_status = "blocked"
            gate_reason = "missing_runtime_apply_or_plan"

        con.execute("""
        insert into decider_tuning_observability_runtime_final_gate
          (proposal_id, gate_status, gate_reason, checked_at, source)
        values
          (?, ?, ?, datetime('now'), 'promoted_tuning_observability_runtime_final_gate_v1')
        on conflict(proposal_id) do update set
          gate_status=excluded.gate_status,
          gate_reason=excluded.gate_reason,
          checked_at=datetime('now'),
          source=excluded.source
        """, (proposal_id, gate_status, gate_reason))
        n += 1

    con.commit()
    print(f"promoted_tuning_observability_runtime_final_gate_done={n}")
finally:
    con.close()
