import sqlite3,time,traceback

DB="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP=20

def tick():
    conn=sqlite3.connect(DB,timeout=30)
    conn.row_factory=sqlite3.Row
    conn.execute("pragma busy_timeout=30000")
    conn.execute("pragma journal_mode=WAL")

    rows=conn.execute("""
    select id,title,coalesce(spec,'') as spec
    from dev_proposals
    where coalesce(status,'')='approved'
      and coalesce(project_decision,'')='execute_now'
      and coalesce(dev_stage,'')='execute_now'
      and coalesce(spec_stage,'')='refined'
      and coalesce(pr_status,'')=''
    order by id asc
    limit 10
    """).fetchall()

    done=0
    for r in rows:
        spec = (r["spec"] or "").strip()
        if not spec:
            continue

        conn.execute("""
        update dev_proposals
        set spec_stage='decomposed',
            pr_status='ready'
        where id=?
        """,(r["id"],))

        try:
            conn.execute("""
            insert into proposal_conversation(proposal_id,role,message,created_at)
            values(?,?,?,datetime('now'))
            """,(r["id"],"assistant","[spec_decomposer_v1] decomposed_and_ready"))
        except Exception:
            pass

        done += 1

    if done:
        conn.commit()
    conn.close()
    print(f"decomposed={done}", flush=True)

def main():
    print("boot_ok", flush=True)
    while True:
        try:
            tick()
        except Exception as e:
            print(repr(e), flush=True)
            print(traceback.format_exc(), flush=True)
        time.sleep(SLEEP)

if __name__=="__main__":
    main()
