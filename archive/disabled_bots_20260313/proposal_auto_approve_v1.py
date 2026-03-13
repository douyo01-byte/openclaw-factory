import sqlite3,os
DB=os.environ["DB_PATH"]
conn=sqlite3.connect(DB)
conn.execute("""
UPDATE dev_proposals
SET status='approved'
WHERE status IS NULL
OR status=''
OR status='open'
""")
conn.commit()
conn.close()
print("auto approved")
