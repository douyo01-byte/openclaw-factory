import os
import sqlite3

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH", "data/openclaw.db")

def main():
    conn = sqlite3.connect(DB)
    conn.execute("""
    create table if not exists decider_tuning_release_plan(
      proposal_id integer primary key,
      release_action text not null,
      release_reason text not null default '',
      planned_at text not null default (datetime('now')),
      source text not null default 'promoted_tuning_release_planner_v1'
    )
    """)
    rows = conn.execute("""
    select
      dp.id,
      coalesce(e.eligibility_status,'') as eligibility_status,
      coalesce(q.release_status,'') as release_status
    from dev_proposals dp
    join decider_tuning_release_queue q on q.proposal_id = dp.id
    left join decider_tuning_eligibility e on e.proposal_id = dp.id
    where coalesce(dp.guard_status,'')='promoted_review_only'
      and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
      and coalesce(q.release_status,'')='queued'
    order by dp.id asc
    """).fetchall()
    done = 0
    for proposal_id, eligibility_status, release_status in rows:
        if eligibility_status == "eligible" and release_status == "queued":
            release_action = "ready_for_release"
            release_reason = "eligible_and_queued"
        else:
            release_action = "blocked"
            release_reason = "not_eligible_or_not_queued"
        conn.execute("""
        insert into decider_tuning_release_plan(
          proposal_id, release_action, release_reason, planned_at, source
        ) values(?,?,?,?, 'promoted_tuning_release_planner_v1')
        on conflict(proposal_id) do update set
          release_action=excluded.release_action,
          release_reason=excluded.release_reason,
          planned_at=excluded.planned_at,
          source='promoted_tuning_release_planner_v1'
        """, (proposal_id, release_action, release_reason, "datetime('now')"))
        conn.execute("""
        update decider_tuning_release_plan
        set planned_at=datetime('now'),
            source='promoted_tuning_release_planner_v1'
        where proposal_id=?
        """, (proposal_id,))
        done += 1
    conn.commit()
    conn.close()
    print(f"promoted_tuning_release_planner_done={done}", flush=True)

if __name__ == "__main__":
    main()
