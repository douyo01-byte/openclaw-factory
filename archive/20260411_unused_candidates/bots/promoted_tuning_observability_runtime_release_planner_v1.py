#!/usr/bin/env python3
import os
import sqlite3

DB = os.environ["DB_PATH"]

con = sqlite3.connect(DB)
try:
    cur = con.cursor()
    cur.execute("""
    create table if not exists decider_tuning_observability_runtime_release_plan (
      proposal_id integer primary key,
      plan_action text not null,
      plan_reason text not null,
      planned_at text not null default (datetime('now')),
      source text not null
    )
    """)
    rows = cur.execute("""
    select dp.id
    from dev_proposals dp
    join decider_tuning_observability_runtime_final_gate g
      on g.proposal_id = dp.id
    join decider_tuning_observability_runtime_release_queue q
      on q.proposal_id = dp.id
    where coalesce(dp.guard_status,'')='observability_runtime_review_only'
      and coalesce(dp.guard_reason,'')='human_review_observability_runtime_applied'
    order by dp.id
    """).fetchall()
    n = 0
    for (proposal_id,) in rows:
        gate = cur.execute("""
        select coalesce(gate_status,''), coalesce(gate_reason,'')
        from decider_tuning_observability_runtime_final_gate
        where proposal_id=?
        """, (proposal_id,)).fetchone()
        queue = cur.execute("""
        select coalesce(queue_status,''), coalesce(queue_note,'')
        from decider_tuning_observability_runtime_release_queue
        where proposal_id=?
        """, (proposal_id,)).fetchone()
        gate_status = gate[0] if gate else ""
        queue_status = queue[0] if queue else ""
        if gate_status == "open_for_observability_runtime_rollout" and queue_status == "queued":
            plan_action = "ready_for_observability_runtime_release"
            plan_reason = "runtime_final_gated_and_queued"
        else:
            plan_action = "blocked"
            plan_reason = "gate_or_queue_missing"
        cur.execute("""
        insert into decider_tuning_observability_runtime_release_plan
          (proposal_id, plan_action, plan_reason, planned_at, source)
        values
          (?, ?, ?, datetime('now'), 'promoted_tuning_observability_runtime_release_planner_v1')
        on conflict(proposal_id) do update set
          plan_action=excluded.plan_action,
          plan_reason=excluded.plan_reason,
          planned_at=datetime('now'),
          source=excluded.source
        """, (proposal_id, plan_action, plan_reason))
        n += 1
    con.commit()
    print(f"promoted_tuning_observability_runtime_release_planner_done={n}")
finally:
    con.close()
