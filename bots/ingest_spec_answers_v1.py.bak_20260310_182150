import os, sqlite3, datetime

DB_PATH=os.environ.get("DB_PATH","data/openclaw.db")
FACTORY_DB_PATH=os.environ.get("FACTORY_DB_PATH")

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def one(conn, q, a=()):
    r=conn.execute(q,a).fetchone()
    return r[0] if r else None

def pid_for_message(d, chat_id, received_at):
    r=d.execute(
        "select proposal_id from tg_prompt_map where chat_id=? and created_at<=? order by id desc limit 1",
        (str(chat_id), str(received_at))
    ).fetchone()
    return int(r[0]) if r else None

def main():
    if not FACTORY_DB_PATH:
        raise SystemExit("FACTORY_DB_PATH required")
    d=sqlite3.connect(DB_PATH, timeout=30)
    d.row_factory=sqlite3.Row
    f=sqlite3.connect(FACTORY_DB_PATH, timeout=30)
    f.row_factory=sqlite3.Row

    rows=d.execute("""
select id,chat_id,coalesce(text,'') as text, coalesce(received_at,datetime('now')) as received_at
from inbox_commands
where processed=0
order by id asc
""").fetchall()

    applied=0
    for r in rows:
        cid=str(r["chat_id"])
        txt=(r["text"] or "").strip()
        if not txt:
            d.execute("update inbox_commands set processed=1,status='skipped',applied_at=? where id=?",(now(),int(r["id"])))
            d.commit()
            continue

        t=txt.lower()
        if t.startswith("/"):
            continue

        pid=pid_for_message(d, cid, r["received_at"])
        if pid is None:
            continue

        st=one(f,"select stage from proposal_state where proposal_id=?",(int(pid),))
        if st != "waiting_answer":
            continue

        f.execute("insert into proposal_conversation(proposal_id,role,message,created_at) values(?,?,?,?)",(int(pid),"user",txt,now()))
        f.execute("update proposal_state set stage='answer_received', pending_question='', pending_questions='', updated_at=? where proposal_id=?",(now(),int(pid)))
        f.commit()

        d.execute("update inbox_commands set processed=1,status='applied',applied_at=? where id=?",(now(),int(r["id"])))
        d.commit()
        applied+=1

    print(f"Done. applied={applied}")

if __name__=="__main__":
    main()
