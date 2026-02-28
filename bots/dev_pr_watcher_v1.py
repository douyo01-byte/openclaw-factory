import os,requests,sqlite3,time

DB=os.environ.get("DB_PATH","data/openclaw.db")
TOKEN=os.environ["GITHUB_TOKEN"]
REPO=os.environ["GITHUB_REPO"]

def gh(path):
    return requests.get(
        f"https://api.github.com/repos/{REPO}{path}",
        headers={"Authorization":f"Bearer {TOKEN}"},
        timeout=30
    ).json()

def run():
    conn=sqlite3.connect(DB)
    conn.row_factory=sqlite3.Row
    prs=conn.execute("select id,pr_number,status from dev_proposals where pr_number is not null").fetchall()
    for r in prs:
        pr=gh(f"/pulls/{r['pr_number']}")
        if "merged_at" in pr and pr["merged_at"]:
            new="merged"
        elif pr.get("state")=="closed":
            new="closed"
        else:
            new="pr_created"
        if new!=r["status"]:
            conn.execute("update dev_proposals set status=? where id=?", (new,r["id"]))
    conn.commit()

if __name__=="__main__":
    run()
