import sqlite3,random,datetime

DB="data/openclaw.db"

ideas=[
"Optimize query performance",
"Improve log rotation",
"Reduce executor latency",
"Enhance PR watcher resilience",
"Improve CI feedback parser",
"Add auto retry for GitHub API",
"Improve proposal ranking logic"
]

conn=sqlite3.connect(DB)
c=conn.cursor()

idea=random.choice(ideas)

c.execute("""
insert into dev_proposals
(title,status,created_at)
values(?,?,?)
""",(idea,"approved",datetime.datetime.utcnow()))

conn.commit()
conn.close()
