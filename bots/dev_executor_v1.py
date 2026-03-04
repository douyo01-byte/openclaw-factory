import os,sqlite3,subprocess,time
from pathlib import Path

DB=os.environ.get("DB_PATH") or "data/openclaw.db"

def db():
    p=str(Path(DB).resolve())
    con=sqlite3.connect(p,timeout=30,isolation_level=None)
    con.execute("PRAGMA journal_mode=WAL")
    return con

def ensure(con):
    con.execute("""
    create table if not exists dev_execution_log(
        id integer primary key autoincrement,
        proposal_id integer,
        status text,
        message text,
        created_at datetime default current_timestamp
    )
    """)

def mark_stage(con,pid,stage):
    con.execute("""
    insert into proposal_state(proposal_id,stage)
    values(?,?)
    on conflict(proposal_id)
    do update set stage=excluded.stage,updated_at=datetime('now')
    """,(pid,stage))

def run_cmd(cmd):
    return subprocess.run(cmd,shell=True,capture_output=True,text=True)

def process(con,pid):
    mark_stage(con,pid,"executing")

    cmd=f'echo "auto change for proposal {pid}" >> executor_test_{pid}.txt'
    r=run_cmd(cmd)

    if r.returncode!=0:
        con.execute(
            "insert into dev_execution_log(proposal_id,status,message) values(?,?,?)",
            (pid,"error",r.stderr)
        )
        mark_stage(con,pid,"error")
        return

    r=run_cmd("git add -A")
    r=run_cmd(f'git commit -m "auto: proposal {pid}"')

    branch=f"auto/proposal-{pid}"
    run_cmd(f"git checkout -B {branch}")
    run_cmd(f"git push -u origin {branch}")

    pr=run_cmd(f'gh pr create --title "Auto proposal {pid}" --body "auto generated" --base main --head {branch}')

    pr_url=pr.stdout.strip().splitlines()[-1] if pr.stdout else ""

    con.execute(
        "update dev_proposals set dev_stage='pr_created',pr_status='open',pr_url=? where id=?",
        (pr_url,pid)
    )

    con.execute(
        "insert into dev_execution_log(proposal_id,status,message) values(?,?,?)",
        (pid,"ok","pr created")
    )

    mark_stage(con,pid,"pr_created")

def main():
    con=db()
    ensure(con)

    while True:
        rows=con.execute("""
        select proposal_id
        from proposal_state
        where stage='approved'
        """).fetchall()

        for (pid,) in rows:
            process(con,pid)

        time.sleep(5)

if __name__=="__main__":
    main()
