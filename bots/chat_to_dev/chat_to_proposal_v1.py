import os
import sqlite3
import hashlib

DB = os.environ.get("DB_PATH", "data/openclaw.db")

def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("select id,text from tg_private_chat_log").fetchall()
    for r in rows:
        text = r["text"]
        if not text.strip():
            continue
        h = hashlib.sha1(text.encode()).hexdigest()[:10]
        exists = conn.execute(
            "select 1 from dev_proposals where description=?",
            (text,),
        ).fetchone()
        if exists:
            continue
        cur = conn.execute(
            "insert into dev_proposals(title,description,branch_name,status) values(?,?,?,?)",
            (text[:80], text, "__tmp__", "approved"),
        )
        pid = cur.lastrowid
        conn.execute(
            "update dev_proposals set branch_name=? where id=?",
            (f"dev/auto-chat-{h}-{pid}", pid),
        )
    conn.commit()
if __name__ == "__main__":
    main()
