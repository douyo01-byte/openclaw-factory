import os
import sqlite3
import time

DB = os.environ["DB_PATH"]

def evaluate(row):
    title = (row["title"] or "").lower()
    if "guard" in title or "safety" in title:
        return "success", 0.9, "safety improvement"
    if "logging" in title:
        return "neutral", 0.6, "internal improvement"
    if "rollback" in title or "revert" in title:
        return "bad", 0.2, "rollback detected"
    return "success", 0.8, "normal merged change"

def can_record_learning(conn, proposal_id):
    merged = conn.execute("""
    select 1
    from ceo_hub_events
    where event_type='merged'
      and proposal_id=?
    limit 1
    """, (proposal_id,)).fetchone()
    if not merged:
        print(f"[learning] skip proposal={proposal_id} reason=not_merged_yet", flush=True)
        return False

    exists = conn.execute("""
    select 1
    from ceo_hub_events
    where event_type='learning_result'
      and proposal_id=?
    limit 1
    """, (proposal_id,)).fetchone()
    if exists:
        print(f"[learning] skip proposal={proposal_id} reason=already_recorded", flush=True)
        return False

    return True

while True:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("""
    create table if not exists ceo_hub_events(
      id integer primary key,
      event_type text,
      title text,
      body text,
      proposal_id integer,
      pr_url text,
      created_at text default (datetime('now')),
      sent_at text
    )
    """)

    rows = conn.execute("""
    select *
    from dev_proposals
    where pr_status='merged'
      and result_type is null
    """).fetchall()

    for r in rows:
        rtype, score, note = evaluate(r)

        conn.execute("""
        update dev_proposals
        set result_type=?,
            result_score=?,
            result_note=?
        where id=?
        """, (rtype, score, note, r["id"]))

        conn.execute("""
        insert or ignore into decision_patterns(token,weight)
        values (?,?)
        """, (rtype, score))

        if can_record_learning(conn, r["id"]):
            conn.execute("""
            insert into ceo_hub_events(event_type,title,body,proposal_id,pr_url)
            values(?,?,?,?,?)
            """, (
                "learning_result",
                f"学  習  反  映  : {r['title']}",
                f"result={rtype} score={score}",
                r["id"],
                r["pr_url"],
            ))
            print(f"[learning] recorded proposal={r['id']}", flush=True)

    conn.commit()

    top = conn.execute("""
    select id,title,result_type,result_score
    from dev_proposals
    where pr_status='merged'
    order by id desc
    limit 10
    """).fetchall()

    print("\n=== Learning Brain v1 ===\n", flush=True)
    for t in top:
        print(tuple(t), flush=True)

    conn.close()
    time.sleep(120)
