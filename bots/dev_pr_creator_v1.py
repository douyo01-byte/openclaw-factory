import os, sqlite3, subprocess, json, traceback

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH")
FACTORY = "/Users/doyopc/AI/openclaw-factory"
REPO = os.environ.get("GITHUB_REPO", "douyo01-byte/openclaw-factory")
GH = "/opt/homebrew/bin/gh"

def sh(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stdout.strip())
    return r.stdout.strip()

def ensure_main_clean():
    sh(["git", "reset", "--hard"], cwd=FACTORY)
    sh(["git", "clean", "-fd"], cwd=FACTORY)
    sh(["git", "checkout", "-f", "main"], cwd=FACTORY)
    sh(["git", "pull", "--ff-only", "origin", "main"], cwd=FACTORY)

def get_existing_pr(branch):
    try:
        out = sh([GH, "pr", "list", "--repo", REPO, "--head", branch, "--state", "open", "--json", "number,url"], cwd=FACTORY)
        arr = json.loads(out)
        if arr:
            return arr[0]
    except:
        pass
    return None

def main():
    conn = sqlite3.connect(DB, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("pragma busy_timeout=30000")

    rows = conn.execute("""
    select id,title,description,branch_name
    from dev_proposals
    where coalesce(project_decision,'')='execute_now'
      and coalesce(dev_stage,'')='execute_now'
      and coalesce(spec_stage,'')='decomposed'
      and coalesce(pr_status,'')='ready'
      and coalesce(processing,0)=0
    order by id desc
    limit 3
    """).fetchall()

    conn.close()
    if not rows:
        return

    for r in rows:
        pid = r["id"]
        title = (r["title"] or f"proposal-{pid}").strip()
        body = (r["description"] or "").strip()
        branch = (r["branch_name"] or f"dev/proposal-{pid}").strip()

        conn = sqlite3.connect(DB, timeout=30)
        conn.execute("pragma busy_timeout=30000")
        conn.execute("update dev_proposals set processing=1 where id=?", (pid,))
        conn.commit()
        conn.close()

        try:
            existing = get_existing_pr(branch)
            if existing:
                conn = sqlite3.connect(DB, timeout=30)
                conn.execute("pragma busy_timeout=30000")
                conn.execute("""
                update dev_proposals
                set pr_number=?,
                    pr_url=?,
                    pr_status='open',
                    dev_stage='pr_created',
                    processing=0
                where id=?
                """, (int(existing["number"]), existing["url"], pid))
                conn.commit()
                conn.close()
                print(f"reuse pid={pid} pr={existing['number']}", flush=True)
                continue

            ensure_main_clean()

            sh(["git", "checkout", "-B", branch], cwd=FACTORY)

            os.makedirs(f"{FACTORY}/dev_autogen", exist_ok=True)
            with open(f"{FACTORY}/dev_autogen/p{pid}.txt", "w", encoding="utf-8") as f:
                f.write((body or title) + "\n")

            sh(["git", "add", "-A"], cwd=FACTORY)

            status = sh(["git", "status", "--porcelain"], cwd=FACTORY)
            if not status.strip():
                existing = get_existing_pr(branch)
                if existing:
                    conn = sqlite3.connect(DB, timeout=30)
                    conn.execute("pragma busy_timeout=30000")
                    conn.execute("""
                    update dev_proposals
                    set pr_number=?,
                        pr_url=?,
                        pr_status='open',
                        dev_stage='pr_created',
                        processing=0
                    where id=?
                    """, (int(existing["number"]), existing["url"], pid))
                    conn.commit()
                    conn.close()
                    print(f"reuse_nochange pid={pid} pr={existing['number']}", flush=True)
                    continue
                else:
                    conn = sqlite3.connect(DB, timeout=30)
                    conn.execute("pragma busy_timeout=30000")
                    conn.execute("update dev_proposals set processing=0 where id=?", (pid,))
                    conn.commit()
                    conn.close()
                    print(f"nochange pid={pid}", flush=True)
                    continue

            sh(["git", "commit", "-m", f"dev: proposal #{pid}"], cwd=FACTORY)
            sh(["git", "push", "-u", "origin", branch, "--force"], cwd=FACTORY)

            try:
                j = sh([
                    GH, "api", f"repos/{REPO}/pulls",
                    "-f", f"title={title}",
                    "-f", f"head={branch}",
                    "-f", "base=main",
                    "-f", f"body={body or title}"
                ], cwd=FACTORY)
                data = json.loads(j)
                pr_number = int(data["number"])
                pr_url = data.get("html_url") or data.get("url") or ""
            except Exception:
                existing = get_existing_pr(branch)
                if not existing:
                    raise
                pr_number = int(existing["number"])
                pr_url = existing["url"]

            conn = sqlite3.connect(DB, timeout=30)
            conn.execute("pragma busy_timeout=30000")
            conn.execute("""
            update dev_proposals
            set pr_number=?,
                pr_url=?,
                pr_status='open',
                dev_stage='pr_created',
                processing=0
            where id=?
            """, (pr_number, pr_url, pid))
            conn.commit()
            conn.close()
            print(f"created pid={pid} pr={pr_number}", flush=True)

        except Exception as e:
            conn = sqlite3.connect(DB, timeout=30)
            conn.execute("pragma busy_timeout=30000")
            conn.execute("update dev_proposals set processing=0 where id=?", (pid,))
            conn.commit()
            conn.close()
            print(repr(e), flush=True)
            print(traceback.format_exc(), flush=True)

if __name__ == "__main__":
    main()
