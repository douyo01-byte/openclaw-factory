import os,requests,sqlite3,time
from oclibs.telegram import send as tg_send

DB=os.environ.get("DB_PATH","data/openclaw.db")
TOKEN=os.environ.get("GITHUB_TOKEN","")
REPO=os.environ.get("GITHUB_REPO","")

def gh(path):
    return requests.get(
        f"https://api.github.com/repos/{REPO}{path}",
        headers={"Authorization":f"Bearer {TOKEN}"},
        timeout=30
    ).json()

def run():
    if not TOKEN or not REPO:
        return

    conn=sqlite3.connect(DB)
    conn.row_factory=sqlite3.Row
    prs=conn.execute("select id,pr_number,status from dev_proposals where pr_number is not null").fetchall()
    for r in prs:
        pr=gh(f"/pulls/{r['pr_number']}")
        if pr.get("merged_at"):
            new="merged"
        elif pr.get("state")=="closed":
            new="closed"
        else:
            new="pr_created"
        if new!=r["status"]:
            conn.execute("update dev_proposals set status=? where id=?", (new,r["id"]))
            tg_send(f"DEV PROPOSAL\nid: {r['id']}\npr_number: {r['pr_number']}\nstatus: {new}\n\nreply:\nok {r['id']}\nhold {r['id']}\nreq {r['id']} <text>")
    conn.commit()

if __name__=="__main__":
    run()
