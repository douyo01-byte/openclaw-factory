import os, sqlite3, time
DB=os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH")
while True:
    con=sqlite3.connect(DB, timeout=30)
    con.execute("pragma busy_timeout=30000")
    con.execute("""
    update dev_proposals
    set project_decision='execute_now',
        dev_stage='execute_now'
    where status='approved'
      and (
        coalesce(project_decision,'')='' or
        coalesce(dev_stage,'')='' or
        coalesce(dev_stage,'')='approved'
      )
    """)
    con.commit()
    con.close()
    time.sleep(2)
