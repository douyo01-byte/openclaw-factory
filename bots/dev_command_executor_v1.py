import os,re,sqlite3

DB=os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH","data/openclaw.db")

def run():
    conn=sqlite3.connect(DB)
    conn.row_factory=sqlite3.Row

    cols=[r["name"] for r in conn.execute("pragma table_info(inbox_commands)").fetchall()]
    has_status="status" in cols
    has_applied="applied_at" in cols
    has_error="error" in cols

    where=[]
    if has_status:
        where.append("(status is null or status='' or status='new')")
    if has_applied:
        where.append("(applied_at is null or applied_at='')")
    w=" and ".join(where) if where else "1=1"

    rows=conn.execute(
        f"select id,from_username,from_name,text from inbox_commands where {w} order by id asc limit 50"
    ).fetchall()

    for r in rows:
        txt=(r["text"] or "").strip()
        m=re.match(r"^(ok|hold)\s+(\d+)\s*$", txt, re.I)
        if m:
            cmd=m.group(1).lower()
            pid=int(m.group(2))
            st="approved" if cmd=="ok" else "hold"
            conn.execute(
                "update dev_proposals set status=?, decided_at=datetime('now'), decided_by=coalesce(?,''), decision_note=coalesce(decision_note,'') where id=?",
                (st, r["from_username"] or r["from_name"] or "", pid)
            )
            if has_status:
                conn.execute("update inbox_commands set status='applied' where id=?", (r["id"],))
            if has_applied:
                conn.execute("update inbox_commands set applied_at=datetime('now') where id=?", (r["id"],))
            continue

        m=re.match(r"^req\s+(\d+)\s+(.+)$", txt, re.I|re.S)
        if m:
            pid=int(m.group(1))
            note=m.group(2).strip()
            who=r["from_username"] or r["from_name"] or ""
            conn.execute(
                "update dev_proposals set status='req', decided_at=datetime('now'), decided_by=coalesce(?,''), decision_note=? where id=?",
                (who, note, pid)
            )
            if has_status:
                conn.execute("update inbox_commands set status='applied' where id=?", (r["id"],))
            if has_applied:
                conn.execute("update inbox_commands set applied_at=datetime('now') where id=?", (r["id"],))
            continue

        if has_status:
            conn.execute("update inbox_commands set status='ignored' where id=?", (r["id"],))
        if has_applied:
            conn.execute("update inbox_commands set applied_at=datetime('now') where id=?", (r["id"],))
        if has_error:
            conn.execute("update inbox_commands set error=? where id=?", ("unrecognized", r["id"]))

    conn.commit()

if __name__=="__main__":
    run()
