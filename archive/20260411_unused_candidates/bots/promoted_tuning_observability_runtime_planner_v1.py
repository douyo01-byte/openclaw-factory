#!/usr/bin/env python3
import os
import sqlite3

DB = os.environ["DB_PATH"]

con = sqlite3.connect(DB)
try:
    con.execute("pragma journal_mode=WAL;")
    con.execute("pragma busy_timeout=5000;")

    con.execute("""
    create table if not exists decider_tuning_observability_runtime_plan (
      proposal_id integer primary key,
      plan_action text not null,
      plan_reason text not null,
      planned_at text not null default (datetime('now')),
      source text not null
    )
    """)

    rows = con.execute("""
    select dp.id
    from dev_proposals dp
    join decider_tuning_observability_runtime_queue q on q.proposal_id = dp.id
    join decider_tuning_observability_runtime_gate g on g.proposal_id = dp.id
    where coalesce(dp.guard_status,'')='observability_core_review_only'
      and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
      and coalesce(q.queue_status,'')='queued'
      and coalesce(g.gate_status,'')='open_for_observability_runtime'
    order by dp.id
    """).fetchall()

    n = 0
    for (proposal_id,) in rows:
        con.execute("""
        insert into decider_tuning_observability_runtime_plan (
          proposal_id, plan_action, plan_reason, planned_at, source
        ) values (
          ?, 'ready_for_observability_runtime', 'runtime_gated_and_queued', datetime('now'),
          'promoted_tuning_observability_runtime_planner_v1'
        )
        on conflict(proposal_id) do update set
          plan_action=excluded.plan_action,
          plan_reason=excluded.plan_reason,
          planned_at=datetime('now'),
          source=excluded.source
        """, (proposal_id,))
        n += 1

    con.commit()
    print(f"promoted_tuning_observability_runtime_planner_done={n}")
finally:
    con.close()
