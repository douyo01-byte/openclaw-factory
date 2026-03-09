import sqlite3,random

DB="data/openclaw.db"

ideas=[
"AI log analytics SaaS",
"GitHub automation toolkit",
"Developer productivity dashboard",
"CI optimization service",
"AI debugging assistant"
]

idea=random.choice(ideas)

conn=sqlite3.connect(DB)
c=conn.cursor()

c.execute("""
insert into dev_proposals
(title,status)
values(?,?)
""",(idea,"approved"))

conn.commit()
conn.close()
