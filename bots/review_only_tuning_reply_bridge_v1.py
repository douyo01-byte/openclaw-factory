import os
import re
import sqlite3

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH", "data/openclaw.db")

def detect_text_col(conn):
    cols = [r[1] for r in conn.execute("pragma table_info(inbox_commands)").fetchall()]
    for name in ("body", "text", "command_text", "message_text", "content", "input_text", "raw_text", "command"):
        if name in cols:
            return name
    raise SystemExit(f"inbox_commands text column not found: {cols}")

PATTERNS = [
    (re.compile(r'^\s*tune\s+ok\s+(\d+)(?:\s+(.*))?$', re.I), "approved"),
    (re.compile(r'^\s*tune\s+reject\s+(\d+)(?:\s+(.*))?$', re.I), "rejected"),
    (re.compile(r'^\s*tune\s+hold\s+(\d+)(?:\s+(.*))?$', re.I), "keep_review"),
]

def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    text_col = detect_text_col(conn)
    rows = conn.execute(f"""
    select id, coalesce({text_col},'') as body
    from inbox_commands
    where coalesce(status,'')='secretary_done'
      and coalesce(router_status,'')=''
    order by id asc
    limit 200
    """).fetchall()

    done = 0

    for r in rows:
        body = str(r["body"] or "").strip()
        cmd_id = int(r["id"])
        matched = None
        review_status = ""
        proposal_id = 0
        note = ""

        for pat, status in PATTERNS:
            m = pat.match(body)
            if m:
                matched = m
                review_status = status
                proposal_id = int(m.group(1))
                note = (m.group(2) or "").strip()
                break

        if not matched:
            continue

        target = conn.execute("""
        select id
        from dev_proposals
        where id=?
          and (
            coalesce(source_ai,'')='decider_threshold_advisor_v1'
            or coalesce(title,'') like '[decider-tuning]%'
          )
          and coalesce(guard_status,'')='review_only'
          and coalesce(guard_reason,'')='decider_tuning_proposal'
        """, (proposal_id,)).fetchone()

        if not target:
            conn.execute("""
            update inbox_commands
            set router_status='tuning_review_target_not_found',
                router_target='review_only_tuning_reply_bridge_v1',
                router_finish_status='ignored'
            where id=?
            """, (cmd_id,))
            done += 1
            continue

        conn.execute("""
        create table if not exists decider_tuning_reviews(
          proposal_id integer primary key,
          review_status text not null,
          review_note text not null default '',
          reviewed_at text not null default (datetime('now')),
          source text not null default 'review_only_tuning_decider_v1'
        )
        """)

        conn.execute("""
        insert into decider_tuning_reviews(
          proposal_id, review_status, review_note, reviewed_at, source
        ) values(?,?,?,datetime('now'),'review_only_tuning_reply_bridge_v1')
        on conflict(proposal_id) do update set
          review_status=excluded.review_status,
          review_note=excluded.review_note,
          reviewed_at=datetime('now'),
          source='review_only_tuning_reply_bridge_v1'
        """, (proposal_id, review_status, note))

        conn.execute("""
        update dev_proposals
        set
          project_decision = case
            when ?='rejected' then 'archive'
            else coalesce(project_decision,'backlog')
          end,
          decision_note = case
            when ?='approved' then 'human_review_approved'
            when ?='rejected' then 'human_review_rejected'
            when ?='keep_review' then 'human_review_keep_review'
            else coalesce(decision_note,'')
          end
        where id=?
        """, (review_status, review_status, review_status, review_status, proposal_id))

        conn.execute("""
        update inbox_commands
        set router_status='tuning_review_applied',
            router_target='review_only_tuning_reply_bridge_v1',
            router_finish_status=?
        where id=?
        """, (review_status, cmd_id))

        done += 1

    conn.commit()
    conn.close()
    print(f"review_only_tuning_reply_bridge_done={done}", flush=True)

if __name__ == "__main__":
    main()
