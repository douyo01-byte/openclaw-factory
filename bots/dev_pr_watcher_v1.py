from __future__ import annotations
import os, sqlite3, subprocess

DB_PATH=os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or "data/openclaw.db"

def gh(path: str):
    out=subprocess.check_output(["gh","api",path], text=True)
    import json
    return json.loads(out)

def tg_send(text: str):
    tok=os.environ["TELEGRAM_BOT_TOKEN"]
    chat=os.environ["TELEGRAM_CHAT_ID"]
    import requests
    requests.post(
        f"https://api.telegram.org/bot{tok}/sendMessage",
        data={"chat_id": chat, "text": text},
        timeout=20,
    ).raise_for_status()

def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn=sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory=sqlite3.Row
    prs=conn.execute("select id,pr_number,coalesce(pr_status,'') pr_status from dev_proposals where pr_number is not null and pr_number!='' and pr_number!=0").fetchall()
    for r in prs:
        pr=gh(f"/repos/douyo01-byte/openclaw-factory/pulls/{r['pr_number']}")
        merged=bool(pr.get("merged_at"))
        state=(pr.get("state") or "").lower()
        if merged:
            new="merged"
        elif state=="closed":
            new="closed"
        else:
            new="open"
        if new!=(r["pr_status"] or ""):
            conn.execute("update dev_proposals set pr_status=? where id=?", (new, r["id"]))
            if new=="merged":
                conn.execute("update dev_proposals set status='merged' where id=? and status!='merged'", (r["id"],))
            conn.commit()
            msg="DEV PROPOSAL\nid: %s\npr_number: %s\npr_status: %s\n\nreply:\nok %s\nhold %s\nreq %s <text>" % (r["id"], r["pr_number"], new, r["id"], r["id"], r["id"])
            tg_send(msg)

if __name__=="__main__":
    raise SystemExit(main())
