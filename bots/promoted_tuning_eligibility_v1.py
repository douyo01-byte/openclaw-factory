import os
import sqlite3

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH", "data/openclaw.db")

def main():
    conn = sqlite3.connect(DB)
    conn.execute("""
    create table if not exists decider_tuning_eligibility(
      proposal_id integer primary key,
      eligibility_status text not null,
      eligibility_reason text not null default '',
      checked_at text not null default (datetime('now')),
      source text not null default 'promoted_tuning_eligibility_v1'
    )
    """)
    rows = conn.execute("""
    select dp.id
    from dev_proposals dp
    where coalesce(dp.guard_status,'')='promoted_review_only'
      and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
    order by dp.id asc
    """).fetchall()

    done = 0
    for (proposal_id,) in rows:
        has_review = conn.execute("""
        select 1
        from decider_tuning_reviews
        where proposal_id=?
          and coalesce(review_status,'')='approved'
        limit 1
        """, (proposal_id,)).fetchone()

        has_promotion = conn.execute("""
        select 1
        from decider_tuning_promotions
        where proposal_id=?
        limit 1
        """, (proposal_id,)).fetchone()

        if has_review and has_promotion:
            status = "eligible"
            reason = "approved_review_and_promoted"
        else:
            status = "blocked"
            if not has_review and not has_promotion:
                reason = "missing_review_and_promotion"
            elif not has_review:
                reason = "missing_approved_review"
            else:
                reason = "missing_promotion"

        conn.execute("""
        insert into decider_tuning_eligibility(
          proposal_id, eligibility_status, eligibility_reason, checked_at, source
        ) values(?,?,?,?,?)
        on conflict(proposal_id) do update set
          eligibility_status=excluded.eligibility_status,
          eligibility_reason=excluded.eligibility_reason,
          checked_at=datetime('now'),
          source=excluded.source
        """, (
            proposal_id,
            status,
            reason,
            sqlite3.connect(":memory:").execute("select datetime('now')").fetchone()[0],
            "promoted_tuning_eligibility_v1",
        ))
        done += 1

    conn.commit()
    conn.close()
    print(f"promoted_tuning_eligibility_done={done}", flush=True)

if __name__ == "__main__":
    main()
