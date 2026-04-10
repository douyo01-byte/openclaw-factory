import os
import sqlite3

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH", "data/openclaw.db")

def main():
    conn = sqlite3.connect(DB)
    conn.execute("""
    create table if not exists decider_tuning_release_gate(
      proposal_id integer primary key,
      gate_status text not null,
      gate_reason text not null,
      checked_at text not null default (datetime('now')),
      source text not null default 'promoted_tuning_release_gate_v1'
    )
    """)
    rows = conn.execute("""
    select
      dp.id,
      case
        when coalesce(dp.guard_status,'')='released_review_only'
         and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
         and r.proposal_id is not null
        then 'open_for_normalization'
        else 'blocked'
      end as gate_status,
      case
        when coalesce(dp.guard_status,'')='released_review_only'
         and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
         and r.proposal_id is not null
        then 'released_and_recorded'
        when coalesce(dp.guard_status,'')='released_review_only'
         and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
         and r.proposal_id is null
        then 'missing_release_row'
        else 'not_released_review_only'
      end as gate_reason
    from dev_proposals dp
    left join decider_tuning_releases r on r.proposal_id = dp.id
    where (
      coalesce(dp.source_ai,'')='decider_threshold_advisor_v1'
      or coalesce(dp.title,'') like '[decider-tuning]%'
      or coalesce(dp.guard_reason,'')='decider_tuning_proposal'
    )
    and (
      coalesce(dp.guard_status,'') in ('promoted_review_only','released_review_only')
      or r.proposal_id is not null
    )
    order by dp.id asc
    """).fetchall()
    done = 0
    for proposal_id, gate_status, gate_reason in rows:
        conn.execute("""
        insert into decider_tuning_release_gate(
          proposal_id, gate_status, gate_reason, checked_at, source
        ) values(?,?,?,?,?)
        on conflict(proposal_id) do update set
          gate_status=excluded.gate_status,
          gate_reason=excluded.gate_reason,
          checked_at=datetime('now'),
          source=excluded.source
        """, (
            proposal_id,
            gate_status,
            gate_reason,
            sqlite3.connect(":memory:").execute("select datetime('now')").fetchone()[0],
            "promoted_tuning_release_gate_v1",
        ))
        done += 1
    conn.commit()
    conn.close()
    print(f"promoted_tuning_release_gate_done={done}", flush=True)

if __name__ == "__main__":
    main()
