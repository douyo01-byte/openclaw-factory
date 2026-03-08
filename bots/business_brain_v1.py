import sqlite3,os,time,random
DB=os.environ["DB_PATH"]

BUSINESS_IDEAS=[
("AI CLI dashboard","Developer productivity dashboard","dev/biz-cli-dashboard"),
("AI automation tool","Automation for developer workflow","dev/biz-ai-cli"),
("OpenClaw workspace","Virtual development workspace","dev/biz-workspace"),
]

while True:
    conn=sqlite3.connect(DB)
    backlog=conn.execute("select count(*) from dev_proposals where status='approved'").fetchone()[0]
    if backlog<2:
        t,d,b=random.choice(BUSINESS_IDEAS)
        conn.execute("""
insert into dev_proposals
(title,description,branch_name,status,spec,source_ai,brain_type,confidence,category)
values (?,?,?,?,?,?,?,?,?)
""",(t,d,b,"approved","auto generated spec","business_brain","business",0.7,"feature"))
        conn.commit()
        print("business idea generated",flush=True)
    conn.close()
    time.sleep(300)
