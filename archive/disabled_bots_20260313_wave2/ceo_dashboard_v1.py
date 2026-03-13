import sqlite3,datetime

DB="data/openclaw.db"

conn=sqlite3.connect(DB)
c=conn.cursor()

def count(q):
    c.execute(q)
    return c.fetchone()[0]

merged=count("select count(*) from dev_proposals where status='merged'")
approved=count("select count(*) from dev_proposals where status='approved'")
idea=count("select count(*) from dev_proposals where status='idea'")
closed=count("select count(*) from dev_proposals where status='closed'")

print("===== OpenClaw CEO Dashboard =====")
print("time:",datetime.datetime.utcnow())
print("merged:",merged)
print("approved:",approved)
print("idea:",idea)
print("closed:",closed)

conn.close()
