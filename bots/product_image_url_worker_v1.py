#!/usr/bin/env python3
import html as html_lib
import os
import re
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))
ROOT = Path(__file__).resolve().parent.parent
FETCH_DIR = ROOT / "data" / "telegram_os_fetch"

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
        where coalesce(current_phase,'')='image_plan_done'
          and coalesce(status,'')='done'
          and coalesce(final_reply_status,'') in ('', 'ready', 'queued')
          and id not in (
            select job_id from conversation_artifacts where artifact_type='product_image_urls_markdown'
          )
        order by id asc
        limit ?
        """,
        (limit,),
    ).fetchall()

def collect_urls(html: str):
    pats = [
        r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"',
        r'<meta[^>]+property="og:image:secure_url"[^>]+content="([^"]+)"',
        r'<img[^>]+src="([^"]+)"',
        r'"image"\s*:\s*\{[^}]*"src"\s*:\s*"([^"]+)"',
        r'"featured_image"\s*:\s*"([^"]+)"',
        r'"featured_media".*?"src"\s*:\s*"([^"]+)"',
    ]
    out = []
    for p in pats:
        for m in re.finditer(p, html, re.I | re.S):
            u = html_lib.unescape(m.group(1)).strip()
            if not u:
                continue
            if u.startswith("//"):
                u = "https:" + u
            if u.startswith("/"):
                continue
            if not u.startswith("http"):
                continue
            if any(x in u.lower() for x in [".jpg", ".jpeg", ".png", ".webp", ".avif"]):
                if u not in out:
                    out.append(u)
    return out[:20]

def build_body(job, urls):
    target = job["target_object"] or "対象商品"
    lines = []
    lines.append(f"# {target} 商品画像URL候補")
    lines.append("")
    if not urls:
        lines.append("候補画像URLは抽出できませんでした。")
        return "\n".join(lines)
    lines.append("## 抽出結果")
    for i, u in enumerate(urls, start=1):
        lines.append(f"{i}. {u}")
    lines.append("")
    lines.append("## 利用方針")
    lines.append("- og:image と商品メイン画像を優先")
    lines.append("- FV用は正面寄り・白背景寄りを優先")
    lines.append("- CTA付近は寄り画像があれば候補化")
    return "\n".join(lines)

def run_once():
    con = connect()
    c = con.cursor()
    rows = fetch_jobs(c, 10)
    done = 0
    for job in rows:
        try:
            html_path = FETCH_DIR / f"job_{job['id']}.html"
            html = html_path.read_text(encoding="utf-8", errors="ignore") if html_path.exists() else ""
            urls = collect_urls(html)
            body = build_body(job, urls)
            c.execute(
                """
                insert into conversation_artifacts(
                  job_id, artifact_type, artifact_title, artifact_body, artifact_path, version, created_at
                ) values(?,?,?,?,?,?,datetime('now'))
                """,
                (job["id"], "product_image_urls_markdown", "product_image_urls", body, "", 1)
            )
            c.execute(
                """
                update conversation_jobs
                set current_phase='product_image_urls_done',
                    updated_at=datetime('now')
                where id=?
                """,
                (job["id"],)
            )
            print(f"product_image_urls_done job_id={job['id']} urls={len(urls)}", flush=True)
            done += 1
        except Exception as e:
            print(f"product_image_urls_error job_id={job['id']} err={e}", flush=True)
    con.commit()
    con.close()
    print(f"product_image_urls_total={done}", flush=True)

if __name__ == "__main__":
    run_once()
