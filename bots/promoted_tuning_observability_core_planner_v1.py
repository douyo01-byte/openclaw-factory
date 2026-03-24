#!/usr/bin/env python3
import os, sqlite3

DB = os.environ["DB_PATH"]

con = sqlite3.connect(DB)
cur = con.cursor()

cur.execute("""
create table if not exists decider_tuning_observability_core_plan(
  proposal_id integer primary key,
  plan_action text not null default '',
  plan_reason text not null default '',
  planned_at text not null default '',
  source text not null default ''
)
""")

cur.execute("""
insert into decider_tuning_observability_core_plan(
  proposal_id, plan_action, plan_reason, planned_at, source
)
select
  dp.id,
  case
    when q.proposal_id is not null
     and g.proposal_id is not null
    then 'ready_for_observability_core'
    else 'blocked'
  end,
  case
    when q.proposal_id is not null
     and g.proposal_id is not null
    then 'core_final_gated_and_queued'
    else 'missing_gate_or_queue'
  end,
  datetime('now'),
  'promoted_tuning_observability_core_planner_v1'
from dev_proposals dp
left join decider_tuning_observability_core_final_gate g on g.proposal_id = dp.id
left join decider_tuning_observability_core_queue q on q.proposal_id = dp.id
where coalesce(dp.guard_status,'')='observability_core_mix_review_only'
  and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
on conflict(proposal_id) do update set
  plan_action=excluded.plan_action,
  plan_reason=excluded.plan_reason,
  planned_at=excluded.planned_at,
  source=excluded.source
""")

con.commit()
con.close()
print("promoted_tuning_observability_core_planner_done=1")
