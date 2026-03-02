import os,sqlite3,subprocess,sys

DB_PATH=os.environ.get("DB_PATH","data/openclaw.db")
CORE_PATH=os.path.expanduser("~/AI/openclaw-factory")

def conn():
    return sqlite3.connect(DB_PATH,timeout=30)

def tick():
    c=conn()
    rows=c.execute("""
    select id from dev_proposals
    where spec_stage='refined'
    """).fetchall()
    for r in rows:
        pid=r[0]
        subprocess.call([
            sys.executable,
            "-m","bots.spec_decompose_v1",
            str(pid)
        ],cwd=CORE_PATH)
        c.execute("""
        update dev_proposals
        set spec_stage='decomposed'
        where id=? and spec_stage='refined'
        """,(pid,))
    c.commit()
    c.close()

if __name__=="__main__":
    tick()
