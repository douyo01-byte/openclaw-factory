import os
import sqlite3
from oclibs.telegram import send as tg_send

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH", "data/openclaw.db")

def send_text(text):
    try:
        r = tg_send(text)
        if isinstance(r, dict):
            return str(r.get("message_id", "") or "")
        return ""
    except Exception:
        raise

def run():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    normal_rows = conn.execute("""
        select id, title, pr_number, pr_url
        from dev_proposals
        where coalesce(notified_at,'')=''
          and (pr_url is not null or pr_number is not null)
          and not (
            coalesce(source_ai,'')='decider_threshold_advisor_v1'
            or coalesce(title,'') like '[decider-tuning]%'
          )
        order by id asc
        limit 20
    """).fetchall()

    for r in normal_rows:
        msg = (
            f"DEV PROPOSAL\n"
            f"id: {r['id']}\n"
            f"title: {r['title'] or ''}\n"
            f"pr: {r['pr_url'] or ''}\n\n"
            f"reply:\n"
            f"ok {r['id']}\n"
            f"hold {r['id']}\n"
            f"req {r['id']} <text>"
        )
        msg_id = send_text(msg)
        conn.execute(
            "update dev_proposals set notified_at=datetime('now'), notified_msg_id=? where id=?",
            (msg_id, r["id"]),
        )

    review_rows = conn.execute("""
        select
          id,
          coalesce(source_ai,'') as source_ai,
          coalesce(title,'') as title,
          coalesce(branch_name,'') as branch_name,
          coalesce(project_decision,'') as project_decision,
          coalesce(decision_note,'') as decision_note,
          coalesce(guard_status,'') as guard_status,
          coalesce(guard_reason,'') as guard_reason
        from dev_proposals
        where coalesce(notified_at,'')=''
          and (
            coalesce(source_ai,'')='decider_threshold_advisor_v1'
            or coalesce(title,'') like '[decider-tuning]%'
          )
          and coalesce(decision_note,'')='human_review_required'
          and coalesce(guard_status,'')='review_only'
          and coalesce(guard_reason,'')='decider_tuning_proposal'
        order by id asc
        limit 20
    """).fetchall()

    for r in review_rows:
        msg = (
            f"[review-only tuning]\n"
            f"id: {r['id']}\n"
            f"title: {r['title']}\n"
            f"branch: {r['branch_name']}\n"
            f"decision: {r['project_decision']}\n"
            f"note: {r['decision_note']}\n"
            f"guard: {r['guard_status']} / {r['guard_reason']}\n\n"
            f"human review only\n"
            f"do not auto-apply"
        )
        msg_id = send_text(msg)
        conn.execute(
            "update dev_proposals set notified_at=datetime('now'), notified_msg_id=? where id=?",
            (msg_id, r["id"]),
        )

    promoted_rows = conn.execute("""
        select
          id,
          coalesce(source_ai,'') as source_ai,
          coalesce(title,'') as title,
          coalesce(branch_name,'') as branch_name,
          coalesce(project_decision,'') as project_decision,
          coalesce(decision_note,'') as decision_note,
          coalesce(guard_status,'') as guard_status,
          coalesce(guard_reason,'') as guard_reason
        from dev_proposals
        where coalesce(promoted_notified_at,'')=''
          and coalesce(guard_status,'')='promoted_review_only'
          and coalesce(guard_reason,'')='decider_tuning_proposal'
        order by id asc
        limit 20
    """).fetchall()
    for r in promoted_rows:
        msg = (
            f"[promoted tuning]\n"
            f"id: {r['id']}\n"
            f"title: {r['title']}\n"
            f"branch: {r['branch_name']}\n"
            f"decision: {r['project_decision']}\n"
            f"note: {r['decision_note']}\n"
            f"guard: {r['guard_status']} / {r['guard_reason']}\n\n"
            f"approved and promoted for backlog tracking\n"
            f"still isolated from normal automation"
        )
        msg_id = send_text(msg)
        conn.execute(
            "update dev_proposals set promoted_notified_at=datetime('now'), promoted_notified_msg_id=? where id=?",
            (msg_id, r["id"]),
        )

    conn.commit()
    conn.close()

if __name__ == "__main__":
    run()
