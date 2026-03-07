import os
import re
import sqlite3

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH", "data/openclaw.db")

def run():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "select id,from_username,from_name,text from inbox_commands where status='new' order by id asc limit 200"
    ).fetchall()
    for r in rows:
        txt = (r["text"] or "").strip()
        txt = re.sub(r"^\s*開 \s*発 \s*提 \s*案 \s*:\s*", "提 案 : ", txt)
        txt_nospace = re.sub(r"\s+", "", txt)
        who = r["from_username"] or r["from_name"] or ""

        m = re.match(r"^提 案 :\s*(.+)$", txt, re.S)
        if m:
            body = m.group(1).strip()
            title = (body.splitlines()[0].strip() if body else "proposal")[:80]
            base = re.sub(r"[^a-z0-9]+", "-", (who or "user").lower()).strip("-")[:24] or "user"
            branch = f"dev/{base}-proposal-{r['id']}"
            conn.execute(
                "insert into dev_proposals(title,description,branch_name,status,created_at,category,target_system,improvement_type,quality_score) values(?,?,?,?,datetime('now'),?,?,?,?)",
                (title, body, branch, "proposed", "automation", "executor", "stabilize", 60),
            )
            conn.execute(
                "update inbox_commands set status='applied', applied_at=datetime('now'), error=null where id=?",
                (r["id"],),
            )
            continue

        m = re.match(r"^(ok|hold)\s+(\d+)\s*$", txt, re.I)
        if m:
            cmd = m.group(1).lower()
            pid = int(m.group(2))
            st = "approved" if cmd == "ok" else "hold"
            conn.execute("update dev_proposals set status=? where id=?", (st, pid))
            conn.execute(
                "update inbox_commands set status='applied', applied_at=datetime('now'), error=null where id=?",
                (r["id"],),
            )
            continue

        m = re.match(r"^req\s+(\d+)\s+(.+)$", txt, re.I | re.S)
        if m:
            pid = int(m.group(1))
            conn.execute("update dev_proposals set status='req' where id=?", (pid,))
            conn.execute(
                "update inbox_commands set status='applied', applied_at=datetime('now'), error=null where id=?",
                (r["id"],),
            )
            continue

        m = re.match(r"^承 認 し ま す #?(\d+)$", txt_nospace)
        if m:
            pid = int(m.group(1))
            conn.execute("update dev_proposals set status='approved' where id=?", (pid,))
            conn.execute(
                "update inbox_commands set status='applied', applied_at=datetime('now'), error=null where id=?",
                (r["id"],),
            )
            continue

        m = re.match(r"^承 認 #?(\d+)$", txt_nospace)
        if m:
            pid = int(m.group(1))
            conn.execute("update dev_proposals set status='approved' where id=?", (pid,))
            conn.execute(
                "update inbox_commands set status='applied', applied_at=datetime('now'), error=null where id=?",
                (r["id"],),
            )
            continue

        m = re.match(r"^保 留 #?(\d+)$", txt_nospace)
        if m:
            pid = int(m.group(1))
            conn.execute("update dev_proposals set status='hold' where id=?", (pid,))
            conn.execute(
                "update inbox_commands set status='applied', applied_at=datetime('now'), error=null where id=?",
                (r["id"],),
            )
            continue

        m = re.match(r"^質 問 #?(\d+)(.+)$", txt_nospace, re.S)
        if m:
            pid = int(m.group(1))
            conn.execute("update dev_proposals set status='needs_info' where id=?", (pid,))
            conn.execute(
                "update inbox_commands set status='applied', applied_at=datetime('now'), error=null where id=?",
                (r["id"],),
            )
            continue

        conn.execute(
            "update inbox_commands set status='ignored', applied_at=datetime('now'), error=? where id=?",
            ("unrecognized", r["id"]),
        )

    conn.commit()
    conn.close()

if __name__ == "__main__":
    run()
