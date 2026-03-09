import sqlite3,datetime

DB="data/openclaw.db"

conn=sqlite3.connect(DB)
c=conn.cursor()

c.execute("""
select id,title
from dev_proposals
where status='approved'
limit 5
""")

rows=c.fetchall()

if rows:

    decision = rows[0][1]

    c.execute("""
    insert into ceo_hub_events(event,created_at)
    values(?,?)
    """,(f"AI_CEO_DECISION:{decision}",datetime.datetime.utcnow()))

conn.commit()
conn.close()
