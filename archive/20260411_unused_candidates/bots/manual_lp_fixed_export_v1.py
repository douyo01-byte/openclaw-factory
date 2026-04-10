from __future__ import annotations
import os
import sys
import sqlite3
from pathlib import Path

DB = os.environ.get("DB_PATH") or f"{Path.home()}/AI/openclaw-factory/data/openclaw.db"
ROOT = Path.home() / "AI" / "openclaw-factory-daemon"
FIXED_DIR = ROOT / "data" / "telegram_os_html" / "fixed"
HTML_DIR = ROOT / "data" / "telegram_os_html"

def db():
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    return con

def main():
    if len(sys.argv) < 3:
        print("usage: manual_lp_fixed_export_v1.py <job_id> <version>")
        raise SystemExit(1)

    job_id = int(sys.argv[1])
    version = int(sys.argv[2])

    fixed = FIXED_DIR / f"job_{job_id}_lp_v{version}_fixed.html"
    if not fixed.exists():
        print(f"fixed_missing={fixed}")
        raise SystemExit(1)

    out = HTML_DIR / f"job_{job_id}_lp_v{version}.html"
    out.write_text(fixed.read_text(encoding="utf-8"), encoding="utf-8")

    con = db()
    cur = con.cursor()

    cur.execute("""
        delete from conversation_artifacts
        where job_id=?
          and artifact_type='public_preview_url'
    """, (job_id,))

    cur.execute("""
        insert into conversation_artifacts(
          job_id, artifact_type, artifact_title, artifact_body, artifact_path, version, created_at
        ) values(?,?,?,?,?,?,datetime('now'))
    """, (
        job_id,
        "lp_html_export_v3",
        f"lp_html_export_v{version}_manual",
        "",
        str(out),
        version
    ))

    cur.execute("""
        update conversation_jobs
        set current_phase='lp_html_export_done',
            final_reply_text='',
            final_reply_status='',
            updated_at=datetime('now')
        where id=?
    """, (job_id,))

    con.commit()
    con.close()
    print(f"manual_export_done job_id={job_id} version={version} path={out}")

if __name__ == "__main__":
    main()
