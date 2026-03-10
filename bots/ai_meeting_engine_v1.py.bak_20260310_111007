import sqlite3,random,datetime

DB="data/openclaw.db"
conn=sqlite3.connect(DB)
c=conn.cursor()

c.execute("""
select id,title
from dev_proposals
where status in ('approved','merged')
order by random()
limit 3
""")
rows=c.fetchall()

if rows:
    discussion=" | ".join([r[1] for r in rows])
    topic=random.choice([
        "executor stability",
        "proposal quality",
        "watcher lifecycle sync",
        "dashboard health metrics",
        "backlog control",
        "proposal supply",
    ])
    impact=random.choice(["high","medium"])
    risk=random.choice(["low","medium"])
    complexity=random.choice(["low","medium","high"])

    body=f"topic={topic}\nimpact={impact}\nrisk={risk}\ncomplexity={complexity}\ndiscussion={discussion}"

    c.execute("""
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

    c.execute("""
    insert into ceo_hub_events(event_type,title,body,created_at)
    values(?,?,?,?)
    """,(
        "ai_meeting",
        f"AI meeting: {topic}",
        body,
        datetime.datetime.now(datetime.UTC).isoformat()
    ))

    proposal_title=f"AI meeting improvement {datetime.datetime.now().strftime('%H%M')}"
    spec=f"""Goal:
Implement: {proposal_title}

Discussion:
- topic: {topic}
- impact: {impact}
- risk: {risk}
- complexity: {complexity}

Context:
{discussion}

Acceptance:
- code compiles
- current pipeline remains operational
- change is limited and reviewable
"""

    c.execute("""
    insert into dev_proposals(
      title,description,spec,status,spec_stage,project_decision,guard_status,guard_reason,
      created_at,category,target_system,improvement_type,quality_score
    ) values(
      ?,?,?,?,'refined','backlog','pending','ai_meeting_refinement',datetime('now'),?,?,?,?
    )
    """,(
        proposal_title,
        spec,
        spec,
        "idea",
        "improvement",
        "core",
        "refinement",
        68
    ))

conn.commit()
conn.close()
