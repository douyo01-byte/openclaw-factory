import os,re,sqlite3

DB=os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH","data/openclaw.db")

def run():
    conn=sqlite3.connect(DB)
    conn.row_factory=sqlite3.Row

    cols=[r["name"] for r in conn.execute("pragma table_info(inbox_commands)").fetchall()]
    has_status="status" in cols
    has_applied="applied_at" in cols
    has_error="error" in cols

    rows=conn.execute(
        "select id,from_username,from_name,text from inbox_commands where status='new' order by id asc limit 200"
    ).fetchall()

    for r in rows:
        txt=(r["text"] or "").strip()
        txt=re.sub(r'^\s*開発提案\s*:\s*','提案: ',txt)

        who=r["from_username"] or r["from_name"] or ""

        m=re.match(r"^提案:\s*(.+)$", txt, re.S)
        if m:
            body=m.group(1).strip()
            title=(body.splitlines()[0].strip() if body else "proposal")[:80]
            base=re.sub(r"[^a-z0-9]+","-",(who or "user").lower()).strip("-")[:24] or "user"
            branch=f"dev/{base}-proposal-{r['id']}"
            conn.execute(
                "insert into dev_proposals(title,description,branch_name,status,risk_level,created_at) values(?,?,?,?,?,datetime('now'))",
                (title, body, branch, 'pending', 'medium')
            )
            conn.execute("update inbox_commands set status='applied', applied_at=datetime('now'), error=null where id=?", (r["id"],))
            continue

        m=re.match(r"^(ok|hold)\s+(\d+)\s*$", txt, re.I)
        if m:
            cmd=m.group(1).lower()
            pid=int(m.group(2))
            st="approved" if cmd=="ok" else "hold"
            conn.execute(
                "update dev_proposals set status=?, decided_at=datetime('now'), decided_by=coalesce(?,''), decision_note=coalesce(decision_note,'') where id=?",
                (st, who, pid)
            )
            conn.execute("update inbox_commands set status='applied', applied_at=datetime('now') where id=?", (r["id"],))
            continue

        m=re.match(r"^req\s+(\d+)\s+(.+)$", txt, re.I|re.S)
        if m:
            pid=int(m.group(1))
            note=m.group(2).strip()
            conn.execute(
                "update dev_proposals set status='req', decided_at=datetime('now'), decided_by=coalesce(?,''), decision_note=? where id=?",
                (who, note, pid)
            )
            conn.execute("update inbox_commands set status='applied', applied_at=datetime('now') where id=?", (r["id"],))
            continue

        m=re.match(r"^承認します\s*#(\d+)\s*$", txt)
        if m:
            pid=int(m.group(1))
            conn.execute(
                "update dev_proposals set status='approved', decided_at=datetime('now'), decided_by=coalesce(?,''), decision_note=coalesce(decision_note,'') where id=?",
                (who, pid)
            )
            conn.execute("update inbox_commands set status='applied', applied_at=datetime('now') where id=?", (r["id"],))
            continue

        if has_error:
            conn.execute("update inbox_commands set error=? where id=?", ("unrecognized", r["id"]))
        conn.execute("update inbox_commands set status='ignored', applied_at=datetime('now') where id=?", (r["id"],))

    conn.commit()

if __name__=="__main__":
    run()
