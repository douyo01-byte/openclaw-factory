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

    c.execute("""
    insert into ceo_hub_events(event,created_at)
    values(?,?)
    """,(f"AI_MEETING:{discussion}",datetime.datetime.utcnow()))

conn.commit()
conn.close()
