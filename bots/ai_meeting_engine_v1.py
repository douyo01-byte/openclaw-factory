import sqlite3,random,datetime

DB="data/openclaw.db"

conn=sqlite3.connect(DB)
c=conn.cursor()

c.execute("""
select id,title
from dev_proposals
where status='approved'
order by random()
limit 3
""")

rows=c.fetchall()

if rows:
    discussion=" | ".join([r[1] for r in rows])
    title = "AI meeting improvement " + datetime.datetime.now(datetime.UTC).strftime("%H%M")
    spec = f"""Goal:
Implement: {title}
Meeting context:
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
      ?,?,?,?,'raw','backlog','pending','ai_meeting_draft',datetime('now'),?,?,?,?
    )
    """,(title,spec,spec,"idea","improvement","core","meeting_followup",60))

    c.execute("""
    insert into ceo_hub_events(event_type,title,body,created_at)
    values(?,?,?,?)
    """,("ai_meeting","AI meeting summary",discussion,datetime.datetime.now(datetime.UTC)))

conn.commit()
conn.close()
