import os
import sqlite3
import time

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def run_once():
    con = sqlite3.connect(DB, timeout=30)
    con.execute("pragma busy_timeout=30000")
    rows = con.execute("""
        select id,
               coalesce(source_ai,''),
               coalesce(status,''),
               coalesce(project_decision,''),
               coalesce(dev_stage,''),
               coalesce(pr_status,''),
               coalesce(impact_score,0),
               coalesce(result_score,0),
               coalesce(title,'')
        from dev_proposals
        where coalesce(status,'') not in ('merged','closed')
    """).fetchall()

    for r in rows:
        pid, source_ai, status, decision, dev_stage, pr_status, impact_score, result_score, title = r
        p = 0
        if source_ai == "cto":
            p += 35
        if source_ai == "coo":
            p += 25
        if decision == "execute_now":
            p += 25
        if status == "approved":
            p += 20
        if pr_status == "open":
            p -= 15
        if dev_stage in ("merged", "closed"):
            p -= 50
        p += int(float(impact_score or 0) * 10)
        p += int(float(result_score or 0))
        t = (title or "").lower()
        if "health" in t or "executor" in t or "merge" in t or "ceo" in t:
            p += 10
        con.execute("update dev_proposals set priority=? where id=?", (p, pid))

    con.commit()

    top = con.execute("""
        select id, title, coalesce(source_ai,''), coalesce(priority,0)
        from dev_proposals
        where coalesce(status,'') not in ('merged','closed')
        order by coalesce(priority,0) desc, id desc
        limit 5
    """).fetchall()
    con.close()

    print("[ceo_priority]", flush=True)
    for x in top:
        print(x, flush=True)

if __name__ == "__main__":
    while True:
        run_once()
        time.sleep(300)
