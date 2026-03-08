import sqlite3,os,time,random
DB=os.environ["DB_PATH"]

KEYWORDS=[
("AI automation tool","GitHub trending automation","dev/market-ai-cli"),
("AI dev dashboard","GitHub dev analytics dashboard","dev/market-dev-dashboard"),
("OpenClaw analytics","Repository analytics tool","dev/market-analytics"),
]

def trending_score():
    return random.random()>0.5

while True:
    try:
        conn=sqlite3.connect(DB)
        backlog=conn.execute("select count(*) from dev_proposals where status='approved'").fetchone()[0]
        if backlog<2 and trending_score():
            t,d,b=random.choice(KEYWORDS)
            conn.execute("""
insert into dev_proposals
(title,description,branch_name,status,spec,source_ai,brain_type,confidence,category)
values (?,?,?,?,?,?,?,?,?)
""",(t,d,b,"approved","auto generated spec","market_brain","market",0.6,"trend"))
            conn.commit()
            print("market opportunity detected",flush=True)
        conn.close()
    except Exception as e:
        print("market brain error:",e,flush=True)
    time.sleep(600)
