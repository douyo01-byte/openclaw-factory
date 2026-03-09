import sqlite3,random,datetime

DB="data/openclaw.db"

ideas=[
"Sell OpenClaw automation toolkit",
"GitHub automation SaaS",
"AI DevOps monitoring SaaS",
"AI code optimization service",
"Developer productivity SaaS"
]

conn=sqlite3.connect(DB)
c=conn.cursor()

idea=random.choice(ideas)

c.execute("""
insert into dev_proposals(title,status)
values(?,?)
""",(f"REVENUE:{idea}","approved"))

c.execute("""
insert into ceo_hub_events(event_type,title,body,created_at)
values(?,?,?,?)
""",(
"revenue",
"AI Revenue Idea",
idea,
datetime.datetime.utcnow()
))

conn.commit()
conn.close()
