import os
import sqlite3

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH", "data/openclaw.db")

def main():
    conn = sqlite3.connect(DB)
    conn.execute("""
    create table if not exists decider_tuning_reviews(
      proposal_id integer primary key,
      review_status text not null,
      review_note text not null default '',
      reviewed_at text not null default (datetime('now')),
      source text not null default 'review_only_tuning_decider_v1'
    )
    """)
    rows = conn.execute("""
    select id
    from dev_proposals
    where (
      coalesce(source_ai,'')='decider_threshold_advisor_v1'
      or coalesce(title,'') like '[decider-tuning]%'
    )
      and coalesce(decision_note,'')='human_review_required'
      and coalesce(guard_status,'')='review_only'
      and coalesce(guard_reason,'')='decider_tuning_proposal'
    order by id asc
    """).fetchall()
    done = 0
    for (proposal_id,) in rows:
        conn.execute("""
        insert or ignore into decider_tuning_reviews(
          proposal_id, review_status, review_note, reviewed_at, source
        ) values(?, 'pending', '', datetime('now'), 'review_only_tuning_decider_v1')
        """, (proposal_id,))
        done += 1
    conn.commit()
    conn.close()
    print(f"decider_tuning_review_seed_done={done}", flush=True)

if __name__ == "__main__":
    main()
