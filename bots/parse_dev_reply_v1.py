import os,sqlite3,re,time

DB=os.environ["DB_PATH"]

def conn():
    c=sqlite3.connect(DB)
    c.row_factory=sqlite3.Row
    return c

while True:
    try:
        with conn() as c:
            rows=c.execute(
            "select * from tg_private_chat_log order by id desc limit 20"
            ).fetchall()

            for r in rows:
                t=r["text"]

                m=re.search(r"承認\s*#(\d+)",t)
                if m:
                    pid=int(m.group(1))
                    c.execute(
                    "update dev_proposals set status='approved' where id=?",
                    (pid,)
                    )

                m=re.search(r"保留\s*#(\d+)",t)
                if m:
                    pid=int(m.group(1))
                    c.execute(
                    "update dev_proposals set status='hold' where id=?",
                    (pid,)
                    )

                m=re.search(r"質問\s*#(\d+)\s*(.*)",t)
                if m:
                    pid=int(m.group(1))
                    msg=m.group(2)
                    c.execute(
                    "insert into proposal_conversation(proposal_id,role,message) values(?,?,?)",
                    (pid,"human",msg)
                    )
                    c.execute(
                    "update proposal_state set stage='answer_received' where proposal_id=?",
                    (pid,)
                    )

            c.commit()
    except:
        pass

    time.sleep(3)
