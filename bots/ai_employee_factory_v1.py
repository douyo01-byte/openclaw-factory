import sqlite3,random,datetime

DB="data/openclaw.db"

roles=[
("Marketing AI","Analyze developer market and propose growth ideas"),
("Sales AI","Design SaaS sales strategies"),
("Research AI","Scan GitHub trends and propose improvements"),
("Product AI","Design new OpenClaw modules"),
("Optimization AI","Improve performance and infrastructure")
]

name,desc=random.choice(roles)

conn=sqlite3.connect(DB)
c=conn.cursor()

c.execute("""
insert into ceo_hub_events(event_type,title,body,created_at)
values(?,?,?,?)
""",(
"ai_employee",
name,
desc,
datetime.datetime.utcnow()
))

conn.commit()
conn.close()
