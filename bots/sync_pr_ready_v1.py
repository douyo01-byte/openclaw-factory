import os, sqlite3, time
DB=os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH")
while True:
    con=sqlite3.connect(DB, timeout=30)
    con.execute("pragma busy_timeout=30000")
    con.execute("""
    update dev_proposals
    set pr_status='ready', processing=0
    where coalesce(dev_stage,'')='execute_now'
      and coalesce(spec_stage,'')='decomposed'
      and coalesce(pr_status,'')=''
    """)
    con.commit()
    con.close()
    time.sleep(2)
