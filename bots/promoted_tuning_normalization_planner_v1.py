import os
import sqlite3

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH", "data/openclaw.db")

def main():
    conn = sqlite3.connect(DB)
    conn.execute("""
    create table if not exists decider_tuning_normalization_plan(
      proposal_id integer primary key,
      normalize_action text not null,
      normalize_reason text not null default '',
      planned_at text not null default (datetime('now')),
      source text not null default 'promoted_tuning_normalization_planner_v1'
    )
    """)
    rows = conn.execute("""
    select
      dp.id,
      coalesce(g.gate_status,'') as gate_status
    from decider_tuning_normalization_queue q
    join dev_proposals dp on dp.id = q.proposal_id
    left join decider_tuning_release_gate g on g.proposal_id = dp.id
    where coalesce(q.queue_status,'')='queued'
      and coalesce(dp.guard_status,'')='released_review_only'
      and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
    order by dp.id asc
    """).fetchall()
    done = 0
    for proposal_id, gate_status in rows:
        if gate_status == 'open_for_normalization':
            action = 'ready_for_normalization'
            reason = 'released_and_queued'
        else:
            action = 'blocked'
            reason = 'gate_not_open'
        conn.execute("""
        insert into decider_tuning_normalization_plan(
          proposal_id, normalize_action, normalize_reason, planned_at, source
        ) values(?,?,?,datetime('now'),'promoted_tuning_normalization_planner_v1')
        on conflict(proposal_id) do update set
          normalize_action=excluded.normalize_action,
          normalize_reason=excluded.normalize_reason,
          planned_at=datetime('now'),
          source='promoted_tuning_normalization_planner_v1'
        """, (
            proposal_id,
            action,
            reason
        ))
        done += 1
    conn.commit()
    conn.close()
    print(f"promoted_tuning_normalization_planner_done={done}", flush=True)

if __name__ == "__main__":
    main()
