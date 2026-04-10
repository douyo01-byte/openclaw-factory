#!/usr/bin/env python3
import os
import sqlite3
from pathlib import Path

DB = os.environ.get("DB_PATH") or str(Path.home() / "AI/openclaw-factory/data/openclaw.db")

con = sqlite3.connect(DB)
con.execute("pragma journal_mode=WAL;")
con.execute("pragma busy_timeout=5000;")

con.execute("""
create table if not exists decider_tuning_observability_runtime_gate (
  proposal_id integer primary key,
  gate_status text,
  gate_reason text,
  checked_at text default (datetime('now')),
  source text
)
""")

rows = con.execute("""
select
  dp.id,
  case
    when a.proposal_id is not null
     and coalesce(p.plan_action,'')='ready_for_observability_core'
    then 'open_for_observability_runtime'
    else 'blocked'
  end as gate_status,
  case
    when a.proposal_id is not null
     and coalesce(p.plan_action,'')='ready_for_observability_core'
    then 'core_applied_and_planned'
    else 'missing_core_apply_or_plan'
  end as gate_reason
from dev_proposals dp
left join decider_tuning_observability_core_applied a on a.proposal_id = dp.id
left join decider_tuning_observability_core_plan p on p.proposal_id = dp.id
where coalesce(dp.guard_status,'')='observability_core_review_only'
  and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
""").fetchall()

for proposal_id, gate_status, gate_reason in rows:
    con.execute("""
    insert into decider_tuning_observability_runtime_gate (
      proposal_id, gate_status, gate_reason, checked_at, source
    ) values (
      ?, ?, ?, datetime('now'), 'promoted_tuning_observability_runtime_gate_v1'
    )
    on conflict(proposal_id) do update set
      gate_status=excluded.gate_status,
      gate_reason=excluded.gate_reason,
      checked_at=excluded.checked_at,
      source=excluded.source
    """, (proposal_id, gate_status, gate_reason))

con.commit()
con.close()
print(f"promoted_tuning_observability_runtime_gate_done={len(rows)}")
