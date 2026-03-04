import os,re,sqlite3,datetime,unicodedata

DB_PATH=os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or "data/openclaw.db"

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def norm(s: str) -> str:
    s=unicodedata.normalize("NFKC", s or "")
    s=re.sub(r"[ \t\r\n\u3000]+","",s)
    return s

def parse_cmd(raw: str):
    t=norm(raw)
    kind=None
    if t.startswith("回答") or t.startswith("回답"):
        kind="answer"
    elif t.startswith("任せます") or t.startswith("任せま"):
        kind="entrust"
    m=re.search(r"#(\d+)", t)
    pid=int(m.group(1)) if m else None
    return kind,pid,t

def tick_once():
    con=sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory=sqlite3.Row
    con.execute("pragma busy_timeout=5000;")

    rows=con.execute(
        "select id,text from inbox_commands "
        "where processed=0 and coalesce(status,'') in ('queued','received','new','') "
        "order by id asc limit 300"
    ).fetchall()

    applied=0
    touched=0
    ignored=0

    for r in rows:
        cmd_id=r["id"]
        kind,pid,t=parse_cmd(r["text"] or "")

        if not kind or not pid:
            con.execute(
                "update inbox_commands set processed=1, status='ignored', applied_at=? where id=?",
                (now(), cmd_id),
            )
            ignored += 1
            continue

        st=con.execute(
            "select stage from proposal_state where proposal_id=?",
            (pid,),
        ).fetchone()

        if not st:
            con.execute(
                "update inbox_commands set processed=1, status='ignored', applied_at=? where id=?",
                (now(), cmd_id),
            )
            ignored += 1
            continue

        stage=(st["stage"] or "")

        if stage != "done" and stage != "answer_received":
            con.execute(
                "update proposal_state set stage=?, updated_at=? where proposal_id=?",
                ("answer_received", now(), pid),
            )
            touched += 1

        con.execute(
            "insert into proposal_conversation(proposal_id,role,message,created_at) values(?,?,?,?)",
            (pid,"user",r["text"],now()),
        )

        con.execute(
            "update inbox_commands set processed=1, status='applied', applied_at=? where id=?",
            (now(), cmd_id),
        )
        applied += 1

    con.commit()
    con.close()
    print("APPLIED", applied, "TOUCHED", touched, "IGNORED", ignored)

if __name__=="__main__":
    tick_once()
