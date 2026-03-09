import os, time, sqlite3, requests

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH", "data/openclaw.db")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = os.environ.get("GITHUB_REPO", "")

def q(query: str):
    r = requests.post(
        "https://api.github.com/graphql",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"query": query},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()

def main():
    if not TOKEN or not REPO:
        print("missing env: GITHUB_TOKEN or GITHUB_REPO", flush=True)
        return

    owner, name = REPO.split("/", 1)

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        "select id, pr_number from dev_proposals "
        "where status in ('approved','pr_created','open') "
        "and pr_number is not null and pr_number!=0 "
        "and coalesce(pr_status,'') not in ('merged','closed') "
        "order by id desc limit 20"
    ).fetchall()

    for row in rows:
        pr = int(row["pr_number"])
        gql = f"""
query {{
  repository(owner:"{owner}", name:"{name}") {{
    pullRequest(number:{pr}) {{
      id
      number
      state
      isDraft
      mergeStateStatus
    }}
  }}
}}
"""
        data = q(gql)
        prn = (data.get("data", {}) or {}).get("repository", {}).get("pullRequest")
        if not prn:
            print(f"[automerge] skip pr={pr} reason=pr_not_found", flush=True)
            continue
        if prn["state"] != "OPEN" or prn["isDraft"]:
            continue
        ms = prn["mergeStateStatus"]
        if ms != "CLEAN":
            if ms == "UNKNOWN":
                print(f"[automerge] skip pr={pr} reason=wait_merge_state:{ms}", flush=True)
                time.sleep(6)
                continue
            print(f"[automerge] skip pr={pr} reason=not_clean:{ms}", flush=True)
            continue

        mg = f"""
mutation {{
  mergePullRequest(input:{{pullRequestId:"{prn['id']}", mergeMethod:MERGE}}) {{
    pullRequest {{ number merged }}
  }}
}}
"""
        out = q(mg)
        errs = out.get("errors") or []
        if errs:
            msg = str(errs[0].get("message", "error"))
            print(f"[automerge] merge failed pr={pr} reason={msg[:200]}", flush=True)
            low = msg.lower()
            if "secondary rate limit" in low or "abuse" in low or "rate limit" in low:
                time.sleep(90)
                break
            continue

        merged = (((out.get("data") or {}).get("mergePullRequest") or {}).get("pullRequest") or {}).get("merged")
        if not merged:
            print(f"[automerge] merge failed pr={pr} reason=merge_not_done", flush=True)
            continue

        conn.execute(
            "update dev_proposals set status='merged', dev_stage='merged', pr_status='merged' where id=?",
            (row["id"],),
        )
        conn.commit()
        print(f"[automerge] merge success pr={pr}", flush=True)

if __name__ == "__main__":
    main()
