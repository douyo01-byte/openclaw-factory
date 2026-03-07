import os,time,sqlite3,subprocess

DB=os.environ["DB_PATH"]

def conn():
    c=sqlite3.connect(DB, timeout=30)
    c.row_factory=sqlite3.Row
    return c

while True:
    try:
        with conn() as c:
            rows=c.execute(
                "select id from dev_proposals where status='approved' and coalesce(quality_score,0) >= 60 and (dev_stage is null or dev_stage='' or dev_stage='approved') order by quality_score desc, id asc limit 5"
            ).fetchall()

            for r in rows:
                pid=r["id"]
                c.execute(
                    "update dev_proposals set dev_stage='executing' where id=? and (dev_stage is null or dev_stage='' or dev_stage='approved')",
                    (pid,),
                )
                if c.total_changes == 0:
                    continue
                c.commit()

                subprocess.run(
                    ["python","-u","bots/dev_executor_v1.py"],
                    check=False,
                )
    except:
        pass

    time.sleep(5)
