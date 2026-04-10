import os
import sqlite3

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH", "data/openclaw.db")

def main():
    conn = sqlite3.connect(DB)
    conn.execute("""
    create table if not exists decider_tuning_normal_merge_plan(
      proposal_id integer primary key,
      merge_action text not null default '',
      merge_reason text not null default '',
      planned_at text not null default '',
      source text not null default ''
    )
    """)
    rows = conn.execute("""
    select
      dp.id,
      coalesce(q.queue_status,'') as queue_status,
      coalesce(g.gate_status,'') as gate_status
    from dev_proposals dp
    join decider_tuning_normal_merge_queue q on q.proposal_id = dp.id
    left join decider_tuning_normalization_gate g on g.proposal_id = dp.id
    where coalesce(q.queue_status,'')='queued'
      and coalesce(dp.guard_status,'')='normalized_review_only'
      and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
    order by dp.id asc
    """).fetchall()
    for proposal_id, queue_status, gate_status in rows:
        if gate_status == "open_for_normal_merge":
            merge_action = "ready_for_normal_merge"
            merge_reason = "normalized_and_queued"
        else:
            merge_action = "blocked"
            merge_reason = "gate_not_open_for_normal_merge"
        conn.execute("""
        insert into decider_tuning_normal_merge_plan(
          proposal_id, merge_action, merge_reason, planned_at, source
        ) values (?, ?, ?, datetime('now'), 'promoted_tuning_normal_merge_planner_v1')
        on conflict(proposal_id) do update set
          merge_action=excluded.merge_action,
          merge_reason=excluded.merge_reason,
          planned_at=excluded.planned_at,
          source=excluded.source
        """, (proposal_id, merge_action, merge_reason))
    conn.commit()
    conn.close()
    print(f"promoted_tuning_normal_merge_planner_done={len(rows)}")

if __name__ == "__main__":
    main()
