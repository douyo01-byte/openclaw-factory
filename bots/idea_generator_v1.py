import os,sqlite3,time,random

DB=os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or "data/openclaw_real.db"

IDEAS=[
"Add health endpoint for daemon monitoring",
"Add CLI command to inspect proposal_state",
"Improve logging format with timestamps",
"Add retry wrapper for GitHub API calls",
"Add metrics export for dev pipeline",
"Refactor spec refiner error handling",
"Add database vacuum scheduler",
"Add watchdog for stuck proposal stages",
"Improve PR title generation",
"Add automatic branch cleanup after merge",
"Add developer activity summary report",
"Improve proposal conversation formatting",
"Add table index optimization migration",
"Add self-test command for daemon bots",
"Add repository size monitoring",
"Improve dev_executor failure reporting",
"Add pipeline visualization JSON export",
"Add system info debug command",
"Improve SQLite connection reuse",
"Add heartbeat record in dev_events",
]

def insert(conn,title):
    conn.execute(
        "insert into dev_proposals(status,dev_stage,title,description,dev_attempts) values(?,?,?,?,0)",
        ("pending","idea",title,title),
    )

def tick():
    conn=sqlite3.connect(DB, timeout=30)
    c=conn.cursor()
    n=c.execute("select count(*) from dev_proposals where status='pending'").fetchone()[0]
    if n<=20:
        k=random.randint(1,3)
        for _ in range(k):
            insert(conn, random.choice(IDEAS))
        conn.commit()
    conn.close()

def main():
    while True:
        try:
            tick()
        except Exception as e:
            print(e,flush=True)
        time.sleep(30)

if __name__=="__main__":
    main()
