#!/usr/bin/env python3
import os
import sqlite3

DB = os.environ.get("DB_PATH") or os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db")

def main():
    con = sqlite3.connect(DB)
    try:
        con.execute("pragma journal_mode=WAL;")
        con.execute("pragma busy_timeout=5000;")
        con.execute("""
        create table if not exists decider_tuning_normal_observability_plan(
          proposal_id integer primary key,
          plan_action text not null default '',
          plan_reason text not null default '',
          planned_at text not null default '',
          source text not null default ''
        )
        """)
        con.execute("""
        insert into decider_tuning_normal_observability_plan(
          proposal_id, plan_action, plan_reason, planned_at, source
        )
        select
          dp.id,
          case
            when coalesce(g.gate_status,'')='open_for_normal_observability'
              then 'ready_for_normal_observability'
            else 'blocked'
          end as plan_action,
          case
            when coalesce(g.gate_status,'')='open_for_normal_observability'
              then 'normal_merged_and_queued'
            else 'gate_not_open_for_normal_observability'
          end as plan_reason,
          datetime('now'),
          'promoted_tuning_normal_observability_planner_v1'
        from dev_proposals dp
        join decider_tuning_normal_observability_queue q on q.proposal_id = dp.id
        left join decider_tuning_normal_observability_gate g on g.proposal_id = dp.id
        where coalesce(q.queue_status,'')='queued'
          and coalesce(dp.guard_status,'')='normal_merged_review_only'
          and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
        on conflict(proposal_id) do update set
          plan_action=excluded.plan_action,
          plan_reason=excluded.plan_reason,
          planned_at=excluded.planned_at,
          source=excluded.source
        """)
        con.commit()
    finally:
        con.close()
    print("promoted_tuning_normal_observability_planner_done=1")

if __name__ == "__main__":
    main()
