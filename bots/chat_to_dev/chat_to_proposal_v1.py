import os,sqlite3,hashlib

DB=os.environ.get("DB_PATH","data/openclaw.db")

def main():
    conn=sqlite3.connect(DB)
    conn.row_factory=sqlite3.Row
    rows=conn.execute("select id,text from tg_private_chat_log").fetchall()
    for r in rows:
        text=r["text"]
        if not text.strip():
            continue
        h=hashlib.sha1(text.encode()).hexdigest()[:10]
        exists=conn.execute("select 1 from dev_proposals where branch_name=?",("dev/auto-chat-"+h,)).fetchone()
        if exists:
            continue
        conn.execute("insert into dev_proposals(title,description,branch_name,status) values(?,?,?,?)",
                     (text[:80],text,"dev/auto-chat-"+h,"approved"))
    conn.commit()

if __name__=="__main__":
    main()
