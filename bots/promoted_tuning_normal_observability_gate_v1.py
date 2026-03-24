import os
import sqlite3

DB = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))

con = sqlite3.connect(DB)
try:
    con.execute("pragma journal_mode=WAL;")
    con.execute("pragma busy_timeout=5000;")
    con.execute("""
    create table if not exists decider_tuning_normal_observability_gate(
      proposal_id integer primary key,
      gate_status text not null default '',
      gate_reason text not null default '',
      checked_at text not null default '',
      source text not null default ''
    )
    """)
    con.execute("""
    insert into decider_tuning_normal_observability_gate(
      proposal_id, gate_status, gate_reason, checked_at, source
    )
    select
      dp.id,
      case
        when nm.proposal_id is not null
         and coalesce(mp.merge_action,'')='ready_for_normal_merge'
        then 'open_for_normal_observability'
        else 'blocked'
      end,
      case
        when nm.proposal_id is not null
         and coalesce(mp.merge_action,'')='ready_for_normal_merge'
        then 'normal_merged_and_recorded'
        else 'not_ready_for_normal_observability'
      end,
      datetime('now'),
      'promoted_tuning_normal_observability_gate_v1'
    from dev_proposals dp
    left join decider_tuning_normal_merges nm on nm.proposal_id = dp.id
    left join decider_tuning_normal_merge_plan mp on mp.proposal_id = dp.id
    where coalesce(dp.guard_status,'')='normal_merged_review_only'
      and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
    on conflict(proposal_id) do update set
      gate_status=excluded.gate_status,
      gate_reason=excluded.gate_reason,
      checked_at=excluded.checked_at,
      source=excluded.source
    """)
    con.commit()
finally:
    con.close()

print("promoted_tuning_normal_observability_gate_done=1")
