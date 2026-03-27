#!/usr/bin/env python3
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))
PUBLIC_REPO = Path(os.environ.get("TELEGRAM_OS_PUBLIC_REPO", os.path.expanduser("~/AI/telegram-os-public")))
PUBLIC_BASE_URL = os.environ.get("TELEGRAM_OS_PUBLIC_BASE_URL", "https://douyo01-byte.github.io/telegram-os-public")

def connect():
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    return con

def fetch_jobs(c, limit=10):
    return c.execute(
        """
        select *
        from conversation_jobs
        where coalesce(current_phase,'') in ('lp_html_export_done','lp_v2_rebuilt_done')
          and coalesce(status,'')='done'
          and id not in (
            select job_id
            from conversation_artifacts
            where artifact_type='public_preview_url'
          )
        order by id asc
        limit ?
        """,
        (limit,),
    ).fetchall()

def get_html_export(c, job_id):
    return c.execute(
        """
        select artifact_path
        from conversation_artifacts
        where job_id=?
          and artifact_type in ('lp_html_export','lp_html_export_v2')
        order by id desc
        limit 1
        """,
        (job_id,),
    ).fetchone()

def ensure_repo():
    if not PUBLIC_REPO.exists():
        raise RuntimeError(f"public_repo_missing:{PUBLIC_REPO}")
    if not (PUBLIC_REPO / ".git").exists():
        raise RuntimeError(f"public_repo_not_git:{PUBLIC_REPO}")

def run(cmd):
    subprocess.run(cmd, cwd=str(PUBLIC_REPO), check=True)

def git_commit_if_needed(message: str) -> bool:
    status = subprocess.check_output(
        ["git", "status", "--porcelain"],
        cwd=str(PUBLIC_REPO),
        text=True
    ).strip()
    if not status:
        return False
    run(["git", "add", "."])
    run(["git", "commit", "-m", message])
    run(["git", "push"])
    return True

def write_root_index():
    p = PUBLIC_REPO / "index.html"
    if not p.exists():
        p.write_text(
            """<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url=./job_19/">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>telegram os public previews</title>
</head>
<body>
  <p>telegram os public previews</p>
</body>
</html>
""",
            encoding="utf-8"
        )
    nojekyll = PUBLIC_REPO / ".nojekyll"
    if not nojekyll.exists():
        nojekyll.write_text("", encoding="utf-8")

def publish_job(job_id: int, html_src: Path) -> str:
    ensure_repo()
    if not html_src.exists():
        raise RuntimeError(f"html_missing:{html_src}")

    job_dir = PUBLIC_REPO / f"job_{job_id}"
    job_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(html_src, job_dir / "index.html")

    write_root_index()
    git_commit_if_needed(f"Publish preview for telegram os job {job_id}")
    return f"{PUBLIC_BASE_URL}/job_{job_id}/"

def run_once():
    con = connect()
    c = con.cursor()
    rows = fetch_jobs(c, 10)
    done = 0

    for job in rows:
        try:
            html_row = get_html_export(c, job["id"])
            if not html_row or not html_row["artifact_path"]:
                raise RuntimeError("lp_html_export_missing")

            url = publish_job(job["id"], Path(html_row["artifact_path"]))

            c.execute(
                """
                insert into conversation_artifacts(
                  job_id, artifact_type, artifact_title, artifact_body, artifact_path, version, created_at
                ) values(?,?,?,?,?,?,datetime('now'))
                """,
                (
                    job["id"],
                    "public_preview_url",
                    "public_preview_url",
                    url,
                    "",
                    1
                )
            )
            c.execute(
                """
                update conversation_jobs
                set current_phase='public_preview_done',
                    updated_at=datetime('now')
                where id=?
                """,
                (job["id"],)
            )
            print(f"public_preview_done job_id={job['id']} url={url}", flush=True)
            done += 1
        except Exception as e:
            print(f"public_preview_error job_id={job['id']} err={e}", flush=True)

    con.commit()
    con.close()
    print(f"public_preview_total={done}", flush=True)

if __name__ == "__main__":
    run_once()
