import os, sqlite3, time

DB=os.environ.get("DB_PATH","/Users/doyopc/AI/openclaw-factory/data/openclaw.db")

def run():
    conn=sqlite3.connect(DB)
    cur=conn.cursor()
    cur.execute("""
    select id,text
    from inbox_commands
    where processed=0
    order by id
    limit 1
    """)
    row=cur.fetchone()

    if not row:
        print("secretary_done=0",flush=True)
        return

    id,text=row

    cur.execute("""
    update inbox_commands
    set processed=1,
        status='company_done',
        applied_at=datetime('now')
    where id=?
    """,(id,))
    conn.commit()
    print("secretary_done=1",flush=True)

if __name__=="__main__":
    while True:
        try:
            run()
        except Exception as e:
            print(e,flush=True)
        time.sleep(5)
