from __future__ import annotations
import os
import sqlite3
from datetime import datetime, UTC

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or "data/openclaw.db"

def now():
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")

def norm(s: str) -> str:
    return " ".join((s or "").strip().split())

def infer_discussion(text: str):
    t = (text or "").lower()
    impact = "medium"
    risk = "medium"
    complexity = "medium"
    system_importance = "medium"
    if any(x in t for x in ["executor", "watcher", "automerge", "spec_refiner", "queue", "lifecycle"]):
        impact = "high"
        system_importance = "core"
    if any(x in t for x in ["db", "schema", "sync", "merge", "state"]):
        complexity = "medium"
    if any(x in t for x in ["revenue", "business", "product"]):
        risk = "medium"
        system_importance = "business"
    if any(x in t for x in ["dashboard", "summary", "visibility", "metrics"]):
        risk = "low"
    if any(x in t for x in ["recovery", "stability", "retry", "guard", "drift", "duplicate"]):
        impact = "high"
        risk = "low"
        complexity = "medium"
        system_importance = "core"
    return impact, risk, complexity, system_importance

def refined_title(base: str, impact: str, risk: str, complexity: str, system_importance: str):
    extra = []
    if impact == "high":
        extra.append("high-impact")
    if risk == "low":
        extra.append("safe-rollout")
    if system_importance == "core":
        extra.append("core")
    if complexity == "medium":
        extra.append("phased")
    suffix = " / ".join(extra[:2])
    if suffix:
        return f"{base} [{suffix}]"
    return base

def main():
    conn = sqlite3.connect(DB, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass

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

    conn.execute("""
    create table if not exists ceo_decision_layer_results(
      proposal_id integer primary key,
      rank_score real default 0,
      meeting_needed integer default 0,
      decision_bucket text default '',
      summary text default '',
      source_snapshot text default '',
      updated_at text default (datetime('now'))
    )
    """)
    rows = conn.execute("""
    select
      p.id,
      coalesce(p.title,'') as title,
      coalesce(p.category,'') as category,
      coalesce(c.rank_score,0) as rank_score,
      coalesce(c.decision_bucket,'') as decision_bucket
    from ceo_decision_layer_results c
    join dev_proposals p on p.id = c.proposal_id
    where coalesce(c.meeting_needed,0)=1
      and (
        coalesce(p.status,'') in ('approved','new','open','execute_now','pr_created','merged')
        or coalesce(p.dev_stage,'') in ('blocked_target_policy','pr_created','execute_now','merged')
      )
      and not exists (
        select 1
        from ceo_hub_events e
        where e.event_type='ai_meeting'
          and e.proposal_id = p.id
      )
    order by c.rank_score desc, p.id desc
    limit 3
    """).fetchall()

    if not rows:
        print("skip=no_meeting_inputs")
        conn.close()
        return

    topics = [norm(r["title"]) for r in rows if norm(r["title"])]
    joined = " | ".join(topics)
    impact, risk, complexity, system_importance = infer_discussion(joined)

    ts = datetime.now(UTC).strftime("%H%M")
    base_title = f"AI meeting improvement {ts}"
    title = refined_title(base_title, impact, risk, complexity, system_importance)

    description = "\n".join([
        "AI meeting generated proposal.",
        f"topics: {joined}",
        "",
        "[discussion]",
        f"impact={impact}",
        f"risk={risk}",
        f"complexity={complexity}",
        f"system_importance={system_importance}",
    ])

    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    branch_name = f"ai-meeting-{stamp}"
    spec = "\n".join([
        f"Goal:",
        f"Implement: {title}",
        "",
        "[discussion]",
        f"impact={impact}",
        f"risk={risk}",
        f"complexity={complexity}",
        f"system_importance={system_importance}",
        "",
        "[refinement]",
        "Use the meeting discussion to keep scope narrow, implementation-ready, and safe for staged rollout.",
        "Prefer observability, recovery, duplicate prevention, and lifecycle consistency where applicable.",
        "",
        "Acceptance:",
        "- code compiles",
        "- current pipeline remains operational",
        "- change is limited and reviewable",
    ])

    conn.execute("""
    insert into dev_proposals(
      title, description, branch_name, spec, status, spec_stage, project_decision, guard_status, guard_reason,
      created_at, category, target_system, improvement_type, quality_score, source_ai
    ) values(
      ?, ?, ?, ?, 'idea', 'raw', 'backlog', 'pending', 'ai_meeting_discussion',
      datetime('now'), 'improvement', 'core', 'refinement', 58, 'ai_meeting_engine_v1'
    )
    """, (title, description, branch_name, spec))
    proposal_id = conn.execute("select last_insert_rowid()").fetchone()[0]

    conn.execute("""
    create table if not exists proposal_conversation(
      id integer primary key autoincrement,
      proposal_id integer,
      role text,
      message text,
      created_at datetime default current_timestamp
    )
    """)

    conn.execute("""
    insert into proposal_conversation(proposal_id, role, message, created_at)
    values(?, 'discussion', ?, ?)
    """, (
        proposal_id,
        "\n".join([
            "[discussion]",
            f"proposal={proposal_id}",
            f"impact={impact}",
            f"risk={risk}",
            f"complexity={complexity}",
            f"system_importance={system_importance}",
            f"topics={joined}",
        ]),
        now(),
    ))

    conn.execute("""
    insert into proposal_conversation(proposal_id, role, message, created_at)
    values(?, 'refinement', ?, ?)
    """, (
        proposal_id,
        "\n".join([
            "[refinement]",
            f"original={base_title}",
            f"refined={title}",
            "refinement_policy=discussion_driven_scope_narrowing",
        ]),
        now(),
    ))

    conn.execute("""
    insert into ceo_hub_events(event_type, title, body, proposal_id, pr_url, created_at)
    values(?, ?, ?, ?, '', ?)
    """, (
        "ai_meeting",
        f"AI会議: {title}",
        "\n".join([
            f"impact={impact}",
            f"risk={risk}",
            f"complexity={complexity}",
            f"system_importance={system_importance}",
            f"topics={joined}",
        ]),
        proposal_id,
        now(),
    ))

    conn.commit()
    conn.close()
    print(f"inserted proposal_id={proposal_id} title={title}")
    print(f"[discussion] impact={impact} risk={risk} complexity={complexity} system_importance={system_importance}")

if __name__ == "__main__":
    main()
