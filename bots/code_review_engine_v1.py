import sqlite3,subprocess,random

DB="data/openclaw.db"

checks=[
"Improve error handling",
"Refactor duplicated logic",
"Optimize database queries",
"Improve logging coverage",
"Reduce API latency",
"Improve retry logic"
]

repo="/Users/doyopc/AI/openclaw-factory"

files=subprocess.check_output(
["git","-C",repo,"ls-files"]
).decode().splitlines()

target=random.choice(files)

proposal=f"{random.choice(checks)} in {target}"

conn=sqlite3.connect(DB)
c=conn.cursor()

c.execute("""
insert into dev_proposals
(title,status)
values(?,?)
""",(proposal,"approved"))

conn.commit()
conn.close()
