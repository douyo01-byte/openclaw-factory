#!/usr/bin/env python3
import os
import sqlite3

DB = os.environ["DB_PATH"]
con = sqlite3.connect(DB)
try:
    cur = con.cursor()
    cur.execute("""
    create table if not exists decider_tuning_observability_runtime_rollout_gate (
      proposal_id integer primary key,
      gate_status text not null,
      gate_reason text not null,
      checked_at text not null default (datetime('now')),
      source text not null
    )
    """)
    rows = cur.execute("""
    select dp.id
    from dev_proposals dp
    join decider_tuning_observability_runtime_release_applied a
      on a.proposal_id = dp.id
    join decider_tuning_observability_runtime_release_plan p
      on p.proposal_id = dp.id
    where coalesce(dp.guard_status,'')='observability_runtime_release_review_only'
      and coalesce(dp.guard_reason,'')='human_review_observability_runtime_release_applied'
      and coalesce(p.plan_action,'')='ready_for_observability_runtime_release'
    order by dp.id
    """).fetchall()
    n = 0
    for (proposal_id,) in rows:
        gate_status = "open_for_observability_runtime_rollout_runtime"
        gate_reason = "runtime_release_applied_and_planned"
        cur.execute("""
        insert into decider_tuning_observability_runtime_rollout_gate
          (proposal_id, gate_status, gate_reason, checked_at, source)
        values
          (?, ?, ?, datetime('now'),
           'promoted_tuning_observability_runtime_rollout_gate_v1')
        on conflict(proposal_id) do update set
          gate_status=excluded.gate_status,
          gate_reason=excluded.gate_reason,
          checked_at=datetime('now'),
          source=excluded.source
        """, (proposal_id, gate_status, gate_reason))
        n += 1
    con.commit()
    print(f"promoted_tuning_observability_runtime_rollout_gate_done={n}")
finally:
    con.close()
