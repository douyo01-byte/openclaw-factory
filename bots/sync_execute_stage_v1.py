import os, sqlite3, time
DB=os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH")
while True:
    con=sqlite3.connect(DB, timeout=30)
    con.execute("pragma busy_timeout=30000")
    con.execute("""
    update dev_proposals
    set dev_stage='execute_now'
    where coalesce(project_decision,'')='execute_now'
      and coalesce(dev_stage,'')=''
    """)
    con.commit()
    con.close()
    time.sleep(2)
