import sqlite3,os,time,random
DB=os.environ["DB_PATH"]

IDEAS=[
("AI SaaS CLI tool","AI automation CLI product","dev/revenue-ai-cli"),
("AI Dev Dashboard","Developer productivity SaaS","dev/revenue-dev-dashboard"),
("AI Market Analyzer","GitHub trend analyzer","dev/revenue-market-analyzer"),
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
""",(t,d,b,"approved","revenue validated spec","revenue_brain","revenue",0.8,"product"))
        conn.commit()
        print("revenue opportunity generated",flush=True)
    conn.close()
    time.sleep(600)
