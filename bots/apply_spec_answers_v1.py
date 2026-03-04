import os,re,sqlite3,datetime,unicodedata

DB_PATH=os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or "data/openclaw.db"

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def norm(s: str) -> str:
    s=unicodedata.normalize("NFKC", s or "")
    s=re.sub(r"[ \t\u3000]+","",s)
    return s

def tick_once():
    con=sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory=sqlite3.Row
    con.execute("pragma busy_timeout=5000;")

    rows=con.execute(
        "select id,text from inbox_commands WHERE status='queued' AND processed=0 order by id asc limit 300"
    ).fetchall()

    applied=0
    touched=0

    for r in rows:
        cmd_id=r["id"]
        t=norm(r["text"])

        m=re.search(r"#(\d+)", t)
        if not m:
            continue

        pid=int(m.group(1))

        st=con.execute("select stage from proposal_state where proposal_id=?", (pid,)).fetchone()
        stage=(st["stage"] if st else "") or ""

        if stage in ("waiting_answer","waiting_answer_user","waiting_spec_answer","waiting","refined"):
            con.execute(
                "update proposal_state set stage=?, updated_at=? where proposal_id=?",
                ("answer_received", now(), pid),
            )
            touched += 1

        con.execute(
            "update inbox_commands set processed=1, status='applied', applied_at=? where id=?",
            (now(), cmd_id),
        )

        applied += 1

    con.commit()
    con.close()
    print("APPLIED", applied, "TOUCHED", touched)

if __name__=="__main__":
    tick_once()
