import os,sqlite3,datetime

DB_PATH=os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or "data/openclaw.db"

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def tick_once():
    con=sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory=sqlite3.Row
    con.execute("pragma busy_timeout=5000;")

    rows=con.execute(
        "select proposal_id from proposal_state "
        "where stage='answer_received' "
        "order by updated_at asc limit 50"
    ).fetchall()

    refined=0

    for r in rows:
        pid=r["proposal_id"]

        msgs=con.execute(
            "select role,message from proposal_conversation "
            "where proposal_id=? order by id asc",
            (pid,)
        ).fetchall()

        if not msgs:
            continue

        # ここでは単純に stage を refined に進める
        con.execute(
            "update proposal_state set stage=?, updated_at=? where proposal_id=?",
            ("refined", now(), pid),
        )

        refined+=1

    con.commit()
    con.close()

    print("REFINED", refined)

if __name__=="__main__":
    tick_once()
