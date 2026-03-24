import os
import sqlite3

DB = os.environ["DB_PATH"]

con = sqlite3.connect(DB)
con.execute("pragma journal_mode=WAL")
con.execute("pragma busy_timeout=5000")

con.execute("""
create table if not exists decider_tuning_observability_core_final_gate(
  proposal_id integer primary key,
  gate_status text not null default '',
  gate_reason text not null default '',
  checked_at text not null default '',
  source text not null default ''
)
""")

con.execute("""
insert into decider_tuning_observability_core_final_gate(
  proposal_id, gate_status, gate_reason, checked_at, source
)
select
  dp.id,
  case
    when a.proposal_id is not null
     and p.proposal_id is not null
     and coalesce(p.mix_action,'')='ready_for_observability_core_mix'
    then 'open_for_observability_core'
    else 'blocked'
  end as gate_status,
  case
    when a.proposal_id is not null
     and p.proposal_id is not null
     and coalesce(p.mix_action,'')='ready_for_observability_core_mix'
    then 'core_mix_applied_and_planned'
    else 'missing_core_mix_prereq'
  end as gate_reason,
  datetime('now'),
  'promoted_tuning_observability_core_final_gate_v1'
from dev_proposals dp
left join decider_tuning_observability_core_mix_applied a on a.proposal_id = dp.id
left join decider_tuning_observability_core_mix_plan p on p.proposal_id = dp.id
where coalesce(dp.guard_status,'')='observability_core_mix_review_only'
  and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
on conflict(proposal_id) do update set
  gate_status=excluded.gate_status,
  gate_reason=excluded.gate_reason,
  checked_at=excluded.checked_at,
  source=excluded.source
""")

con.commit()
con.close()
print("promoted_tuning_observability_core_final_gate_done=1")
