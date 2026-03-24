#!/usr/bin/env python3
import os
import sqlite3

DB = os.environ["DB_PATH"]

con = sqlite3.connect(DB)
try:
    cur = con.cursor()
    cur.execute("""
    create table if not exists decider_tuning_observability_runtime_rollout_plan (
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
    join decider_tuning_observability_runtime_rollout_gate g
      on g.proposal_id = dp.id
    join decider_tuning_observability_runtime_rollout_queue q
      on q.proposal_id = dp.id
    where coalesce(dp.guard_reason,'')='human_review_observability_runtime_release_applied'
      and coalesce(g.gate_status,'')='open_for_observability_runtime_rollout_runtime'
      and coalesce(q.queue_status,'')='queued'
    order by dp.id
    """).fetchall()
    n = 0
    for (proposal_id,) in rows:
        cur.execute("""
        insert into decider_tuning_observability_runtime_rollout_plan
          (proposal_id, plan_action, plan_reason, planned_at, source)
        values
          (?, 'ready_for_observability_runtime_rollout', 'runtime_rollout_gated_and_queued', datetime('now'), 'promoted_tuning_observability_runtime_rollout_planner_v1')
        on conflict(proposal_id) do update set
          plan_action=excluded.plan_action,
          plan_reason=excluded.plan_reason,
          planned_at=datetime('now'),
          source=excluded.source
        """, (proposal_id,))
        n += 1
    con.commit()
    print(f"promoted_tuning_observability_runtime_rollout_planner_done={n}")
finally:
    con.close()
