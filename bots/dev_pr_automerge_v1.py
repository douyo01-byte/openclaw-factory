import os,sqlite3,requests

DB=os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH","data/openclaw.db")
TOKEN=os.environ.get("GITHUB_TOKEN","")
REPO=os.environ.get("GITHUB_REPO","")

def q(path):
    r=requests.post(
        "https://api.github.com/graphql",
        headers={"Authorization":f"Bearer {TOKEN}"},
        json={"query":path},
        timeout=30
    )
    r.raise_for_status()
    return r.json()

def main():
    if not TOKEN or not REPO:
        return

    conn=sqlite3.connect(DB); conn.row_factory=sqlite3.Row
    rows=conn.execute("select id, pr_number from dev_proposals where status in ('approved','pr_created') and pr_number is not null").fetchall()
    for row in rows:
        pr=row["pr_number"]
        gql=f"""
query {{
  repository(owner:"{REPO.split('/')[0]}", name:"{REPO.split('/')[1]}") {{
    pullRequest(number:{pr}) {{
      id
      mergeStateStatus
      isDraft
      state
    }}
  }}
}}
"""
        data=q(gql)
        prn=data["data"]["repository"]["pullRequest"]
        if not prn or prn["state"]!="OPEN" or prn["isDraft"]:
            continue
        if prn["mergeStateStatus"]!="CLEAN":
            continue
        mg=f"""
mutation {{
  mergePullRequest(input:{{pullRequestId:"{prn['id']}", mergeMethod:MERGE}}) {{
    pullRequest {{ number merged }}
  }}
}}
"""
        q(mg)
        conn.execute("update dev_proposals set status='merged', dev_stage='merged' where id=?", (row["id"],))
    conn.commit()

if __name__=="__main__":
    main()
