import sqlite3, os

DB=os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH","data/openclaw.db")

def run():
    conn=sqlite3.connect(DB)
    conn.row_factory=sqlite3.Row
    rows=conn.execute("select id,description from dev_proposals where status='approved' and spec_stage='raw'").fetchall()
    for r in rows:
        pid=r["id"]
        desc=(r["description"] or "").strip()
        parts=[p.strip() for p in desc.replace("\n"," ").split("。") if p.strip()]
        for i,p in enumerate(parts,1):
            conn.execute(
                "insert into dev_proposals(title,description,branch_name,status,spec_stage) values(?,?,?,?,?)",
                (f"{pid}-sub{i}",p,f"dev/sub-{pid}-{i}","approved","decomposed")
            )
        conn.execute("update dev_proposals set spec_stage='done' where id=?", (pid,))
        conn.commit()

if __name__=="__main__":
    run()
