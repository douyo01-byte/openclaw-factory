import os
import sqlite3

DB = os.environ["DB_PATH"]

con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute("pragma journal_mode=WAL;")
cur.execute("pragma busy_timeout=5000;")

cur.execute("""
create table if not exists decider_tuning_observability_core_mix_plan(
  proposal_id integer primary key,
  mix_action text not null default '',
  mix_reason text not null default '',
  planned_at text not null default '',
  source text not null default ''
)
""")

cur.execute("""
insert into decider_tuning_observability_core_mix_plan(
  proposal_id, mix_action, mix_reason, planned_at, source
)
select
  dp.id,
  case
    when a.proposal_id is not null
     and g.gate_status='open_for_observability_core_mix'
     and q.queue_status='queued'
    then 'ready_for_observability_core_mix'
    else 'blocked'
  end,
  case
    when a.proposal_id is not null
     and g.gate_status='open_for_observability_core_mix'
     and q.queue_status='queued'
    then 'normal_observability_applied_and_queued'
    else 'gate_or_queue_missing'
  end,
  datetime('now'),
  'promoted_tuning_observability_core_mix_planner_v1'
from dev_proposals dp
join decider_tuning_observability_core_mix_gate g on g.proposal_id = dp.id
left join decider_tuning_normal_observability_applied a on a.proposal_id = dp.id
left join decider_tuning_observability_core_mix_queue q on q.proposal_id = dp.id
where coalesce(dp.guard_status,'')='normal_observability_review_only'
  and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
on conflict(proposal_id) do update set
  mix_action=excluded.mix_action,
  mix_reason=excluded.mix_reason,
  planned_at=excluded.planned_at,
  source=excluded.source
""")

con.commit()
con.close()
print("promoted_tuning_observability_core_mix_planner_done=1")
