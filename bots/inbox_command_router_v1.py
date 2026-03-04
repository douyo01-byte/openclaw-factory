import os,time,re,sqlite3,unicodedata
from pathlib import Path

DB_PATH=os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or "data/openclaw.db"

def rp(p:str)->str:
    return str(Path(p).resolve())

def db():
    p=rp(DB_PATH)
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    con=sqlite3.connect(p, timeout=30, isolation_level=None)
    con.execute("PRAGMA busy_timeout=8000")
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    return con

def ensure(con):
    con.execute("create table if not exists inbox_commands(id integer primary key autoincrement, status text, text text, created_at text default (datetime('now')))")
    con.execute("create index if not exists idx_inbox_commands_status on inbox_commands(status)")
    con.execute("create index if not exists idx_inbox_commands_created_at on inbox_commands(created_at)")
    con.execute("create table if not exists proposal_state (proposal_id integer primary key, stage text, pending_questions text, updated_at datetime default current_timestamp)")
    con.execute("create table if not exists proposal_conversation (id integer primary key autoincrement, proposal_id integer, role text, message text, created_at datetime default current_timestamp)")

def norm(s:str)->str:
    t=unicodedata.normalize("NFKC", s or "")
    t=re.sub(r"\s+","",t)
    return t

def set_stage(con, pid:int, stage:str):
    con.execute(
        "insert into proposal_state(proposal_id,stage) values(?,?) "
        "on conflict(proposal_id) do update set stage=excluded.stage, updated_at=datetime('now')",
        (pid,stage),
    )

def apply_one(con, cid:int, raw:str):
    t=norm(raw)

    if t in ("ping","/ping"):
        con.execute("update inbox_commands set status='applied' where id=?", (cid,))
        return

    m=re.match(r"^承認#(\d+)$", t)
    if m:
        pid=int(m.group(1))
        con.execute("update dev_proposals set status='approved' where id=?", (pid,))
        set_stage(con,pid,"approved")
        con.execute("insert into proposal_conversation(proposal_id,role,message) values(?,?,?)", (pid,"user",raw))
        con.execute("update inbox_commands set status='applied' where id=?", (cid,))
        return

    m=re.match(r"^保留#(\d+)$", t)
    if m:
        pid=int(m.group(1))
        con.execute("update dev_proposals set status='on_hold' where id=?", (pid,))
        set_stage(con,pid,"on_hold")
        con.execute("insert into proposal_conversation(proposal_id,role,message) values(?,?,?)", (pid,"user",raw))
        con.execute("update inbox_commands set status='applied' where id=?", (cid,))
        return

    m=re.match(r"^回答#(\d+)(.+)$", t)
    if m:
        pid=int(m.group(1))
        ans=m.group(2)
        con.execute("insert into proposal_conversation(proposal_id,role,message) values(?,?,?)", (pid,"user",ans))
        set_stage(con,pid,"answer_received")
        con.execute("update inbox_commands set status='applied' where id=?", (cid,))
        return

    con.execute("update inbox_commands set status='ignored' where id=?", (cid,))

def main():
    con=db()
    ensure(con)
    while True:
        rows=con.execute("select id,text from inbox_commands where status='pending' order by id asc limit 200").fetchall()
        for cid,raw in rows:
            try:
                apply_one(con, int(cid), raw or "")
            except Exception:
                con.execute("update inbox_commands set status='error' where id=?", (cid,))
        time.sleep(1)

if __name__=="__main__":
    main()
