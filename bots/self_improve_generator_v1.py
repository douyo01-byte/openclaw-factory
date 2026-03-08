import sqlite3,os,time,random
DB=os.environ["DB_PATH"]

IDEAS=[
("Watcher reliability","Improve PR watcher stability","dev/self-watch-rel"),
("Logging improvement","Improve daemon logging","dev/self-log-improve"),
("Executor safety","Improve executor safety","dev/self-exec-safe"),
]

while True:
    conn=sqlite3.connect(DB)
    backlog=conn.execute("select count(*) from dev_proposals where status='approved'").fetchone()[0]
    if backlog<2:
        t,d,b=random.choice(IDEAS)
        conn.execute("""
insert into dev_proposals
(title,description,branch_name,status,spec,source_ai,brain_type,confidence,category)
values (?,?,?,?,?,?,?,?,?)
""",(t,d,b,"approved","auto generated spec","self_improve","internal",0.9,"improvement"))
        conn.commit()
        print("self improvement proposal created",flush=True)
    conn.close()
    time.sleep(120)
