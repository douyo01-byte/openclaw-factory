import sqlite3,time,os

DB=os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

while True:
    con=sqlite3.connect(DB)
    c=con.cursor()

    r=c.execute("""
    select count(*) from router_tasks
    where status in ('new','started')
    """).fetchone()[0]

    con.close()

    if r>20:
        print("ROUTER STALL DETECTED:",r)
        os.system("pkill -f task_router_v1 || true")

    time.sleep(30)
