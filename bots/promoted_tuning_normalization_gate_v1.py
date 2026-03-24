import os
import sqlite3

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH", "data/openclaw.db")

def main():
    conn = sqlite3.connect(DB)
    conn.execute("""
    create table if not exists decider_tuning_normalization_gate(
      proposal_id integer primary key,
      gate_status text not null default '',
      gate_reason text not null default '',
      checked_at text not null default (datetime('now')),
      source text not null default 'promoted_tuning_normalization_gate_v1'
    )
    """)
    rows = conn.execute("""
    select
      dp.id,
      case
        when n.proposal_id is not null
         and coalesce(p.normalize_action,'')='ready_for_normalization'
        then 'open_for_normal_merge'
        else 'blocked'
      end as gate_status,
      case
        when n.proposal_id is not null
         and coalesce(p.normalize_action,'')='ready_for_normalization'
        then 'normalized_and_recorded'
        else 'missing_normalization_requirements'
      end as gate_reason
    from dev_proposals dp
    left join decider_tuning_normalizations n on n.proposal_id = dp.id
    left join decider_tuning_normalization_plan p on p.proposal_id = dp.id
    where coalesce(dp.guard_status,'')='normalized_review_only'
      and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
    order by dp.id asc
    """).fetchall()
    for proposal_id, gate_status, gate_reason in rows:
        conn.execute("""
        insert into decider_tuning_normalization_gate(
          proposal_id, gate_status, gate_reason, checked_at, source
        ) values(
          ?, ?, ?, datetime('now'), 'promoted_tuning_normalization_gate_v1'
        )
        on conflict(proposal_id) do update set
          gate_status=excluded.gate_status,
          gate_reason=excluded.gate_reason,
          checked_at=datetime('now'),
          source='promoted_tuning_normalization_gate_v1'
        """, (proposal_id, gate_status, gate_reason))
    conn.commit()
    conn.close()
    print(f"promoted_tuning_normalization_gate_done={len(rows)}")

if __name__ == "__main__":
    main()
