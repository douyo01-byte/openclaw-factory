import os,sqlite3
from oclibs.telegram import send as tg_send

DB=os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH","data/openclaw.db")

def run():
    conn=sqlite3.connect(DB)
    conn.row_factory=sqlite3.Row
    rows=conn.execute(
        "select id,title,pr_number,pr_url from dev_proposals where notified_at is null and (pr_url is not null or pr_number is not null) order by id asc limit 20"
    ).fetchall()
    for r in rows:
        tg_send(f"DEV PROPOSAL\nid: {r['id']}\ntitle: {r['title'] or ''}\npr: {r['pr_url'] or ''}\n\nreply:\nok {r['id']}\nhold {r['id']}\nreq {r['id']} <text>")
        conn.execute("update dev_proposals set notified_at=datetime('now') where id=?", (r["id"],))
    conn.commit()

if __name__=="__main__":
    run()
