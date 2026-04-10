#!/usr/bin/env python3
from __future__ import annotations
import os
import re
import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlparse
import requests

DB = os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
ROOT = Path("/Users/doyopc/AI/openclaw-factory-daemon")
OUT_DIR = ROOT / "data" / "reference_lp"
URL_RE = re.compile(r'https?://[^\s<>"\')]+')

def conn() -> sqlite3.Connection:
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    try:
        con.execute("pragma journal_mode=WAL")
    except Exception:
        pass
    return con

def ensure_schema(c: sqlite3.Cursor) -> None:
    c.execute("""
        create table if not exists reference_lp_sources(
          id integer primary key autoincrement,
          job_id integer not null,
          source_url text not null,
          source_domain text not null default '',
          local_path text not null default '',
          status text not null default 'new',
          note text not null default '',
          created_at text not null default (datetime('now')),
          updated_at text not null default (datetime('now'))
        )
    """)
    c.execute("create index if not exists idx_reference_lp_sources_job on reference_lp_sources(job_id, status)")
    cols = {r["name"] for r in c.execute("pragma table_info(conversation_artifacts)").fetchall()}
    if "artifact_path" not in cols:
        c.execute("alter table conversation_artifacts add column artifact_path text")
    if "version" not in cols:
        c.execute("alter table conversation_artifacts add column version integer default 1")

def extract_urls(text: str) -> list[str]:
    seen = set()
    out = []
    for u in URL_RE.findall(text or ""):
        u = u.strip().rstrip(".,)")
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out

def pick_reference_urls(text: str) -> list[str]:
    urls = extract_urls(text)
    refs = []
    for u in urls:
        host = (urlparse(u).netloc or "").lower()
        if "sankoudesign.com" in host:
            refs.append(u)
        elif "kuu-medic.com" not in host and "kuu-medic.jp" not in host:
            refs.append(u)
    return refs

def fetch_jobs(c: sqlite3.Cursor, limit: int) -> list[sqlite3.Row]:
    return c.execute("""
        select *
        from conversation_jobs
        where coalesce(domain,'')='creative'
          and (
            lower(coalesce(request_text,'')) like '%sankoudesign.com%'
            or lower(coalesce(request_text,'')) like '%参考lp%'
            or lower(coalesce(request_text,'')) like '%参考 url%'
            or lower(coalesce(request_text,'')) like '%参考url%'
          )
          and id not in (
            select job_id
            from reference_lp_sources
            where coalesce(status,'') in ('done','partial')
          )
        order by id asc
        limit ?
    """, (limit,)).fetchall()

def save_artifact(c: sqlite3.Cursor, job_id: int, title: str, body: str, path: str, version: int) -> None:
    c.execute("""
        insert into conversation_artifacts(
          job_id, artifact_type, artifact_title, artifact_body, artifact_path, version, created_at
        ) values(?,?,?,?,?,?,datetime('now'))
    """, (job_id, "reference_lp_html", title, body, path, version))

def fetch_html(url: str) -> str:
    r = requests.get(
        url,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        },
    )
    r.raise_for_status()
    r.encoding = r.encoding or r.apparent_encoding or "utf-8"
    return r.text

def write_html(job_id: int, idx: int, html: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    p = OUT_DIR / f"job_{job_id}_ref_{idx}.html"
    p.write_text(html, encoding="utf-8")
    return p

def run_once(limit: int = 5) -> None:
    con = conn()
    c = con.cursor()
    ensure_schema(c)
    rows = fetch_jobs(c, limit)
    done = 0
    for job in rows:
        refs = pick_reference_urls(job["request_text"] or "")
        if not refs:
            c.execute("""
                insert into reference_lp_sources(job_id, source_url, source_domain, status, note, updated_at)
                values(?,?,?,?,?,datetime('now'))
            """, (job["id"], "", "", "skipped", "no_reference_url"))
            print(f"reference_skip job_id={job['id']} reason=no_reference_url", flush=True)
            continue
        ok = 0
        for idx, url in enumerate(refs, start=1):
            host = (urlparse(url).netloc or "").lower()
            try:
                html = fetch_html(url)
                out = write_html(job["id"], idx, html)
                c.execute("""
                    insert into reference_lp_sources(
                      job_id, source_url, source_domain, local_path, status, note, updated_at
                    ) values(?,?,?,?,?,?,datetime('now'))
                """, (job["id"], url, host, str(out), "done", ""))
                save_artifact(
                    c,
                    job["id"],
                    f"reference_lp_{idx}",
                    f"url={url}\ndomain={host}\npath={out}",
                    str(out),
                    idx,
                )
                ok += 1
                print(f"reference_done job_id={job['id']} idx={idx} url={url}", flush=True)
            except Exception as e:
                c.execute("""
                    insert into reference_lp_sources(
                      job_id, source_url, source_domain, local_path, status, note, updated_at
                    ) values(?,?,?,?,?,?,datetime('now'))
                """, (job["id"], url, host, "", "error", str(e)[:1000]))
                print(f"reference_error job_id={job['id']} idx={idx} url={url} err={e}", flush=True)
        if ok > 0:
            c.execute("""
                update conversation_jobs
                set current_phase='reference_lp_ingested',
                    updated_at=datetime('now')
                where id=?
            """, (job["id"],))
            done += 1
        else:
            c.execute("""
                update conversation_jobs
                set updated_at=datetime('now')
                where id=?
            """, (job["id"],))
    con.commit()
    con.close()
    print(f"reference_ingest_total={done}", flush=True)

def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    run_once(limit)

if __name__ == "__main__":
    main()
