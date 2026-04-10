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
A_RE = re.compile(r'<a[^>]+href=["\']([^"\']+)["\']', re.I)

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
    cols = {r["name"] for r in c.execute("pragma table_info(reference_lp_sources)").fetchall()}
    if "parent_source_id" not in cols:
        c.execute("alter table reference_lp_sources add column parent_source_id integer default 0")

def fetch_jobs(c: sqlite3.Cursor, limit: int) -> list[sqlite3.Row]:
    return c.execute("""
        select *
        from conversation_jobs
        where coalesce(current_phase,'') in ('reference_lp_ingested','reference_lp_pattern_done','reference_lp_expanded')
        order by id asc
        limit ?
    """, (limit,)).fetchall()

def fetch_root_sources(c: sqlite3.Cursor, job_id: int) -> list[sqlite3.Row]:
    return c.execute("""
        select *
        from reference_lp_sources
        where job_id=?
          and coalesce(status,'')='done'
          and coalesce(parent_source_id,0)=0
        order by id asc
    """, (job_id,)).fetchall()

def clear_old_children(c: sqlite3.Cursor, source_id: int) -> None:
    rows = c.execute("""
        select local_path
        from reference_lp_sources
        where coalesce(parent_source_id,0)=?
    """, (source_id,)).fetchall()
    for r in rows:
        p = (r["local_path"] or "").strip()
        if p:
            try:
                Path(p).unlink(missing_ok=True)
            except Exception:
                pass
    c.execute("delete from reference_lp_sources where coalesce(parent_source_id,0)=?", (source_id,))

def extract_candidate_urls(base_url: str, html: str) -> list[str]:
    out = []
    seen = set()
    for href in A_RE.findall(html):
        href = href.strip()
        if not href.startswith("http"):
            continue
        host = (urlparse(href).netloc or "").lower()
        path = (urlparse(href).path or "").lower()
        if "sankoudesign.com" in host:
            continue
        if not host:
            continue
        if any(x in path for x in ["/wp-content/", "/tag/", "/category/"]):
            continue
        if href not in seen:
            seen.add(href)
            out.append(href)
    return out

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

def write_html(job_id: int, source_id: int, idx: int, html: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    p = OUT_DIR / f"job_{job_id}_source_{source_id}_child_{idx}.html"
    p.write_text(html, encoding="utf-8")
    return p

def run_once(limit: int = 5, max_links: int = 12) -> None:
    con = conn()
    c = con.cursor()
    ensure_schema(c)
    rows = fetch_jobs(c, limit)
    done = 0
    for job in rows:
        roots = fetch_root_sources(c, job["id"])
        job_done = False
        for root in roots:
            try:
                clear_old_children(c, root["id"])
                root_html = Path(root["local_path"]).read_text(encoding="utf-8", errors="ignore")
                candidates = extract_candidate_urls(root["source_url"], root_html)[:max_links]
                ok = 0
                for idx, url in enumerate(candidates, start=1):
                    try:
                        html = fetch_html(url)
                        out = write_html(job["id"], root["id"], idx, html)
                        c.execute("""
                            insert into reference_lp_sources(
                              job_id, source_url, source_domain, local_path, status, note, updated_at, parent_source_id
                            ) values(?,?,?,?,?,?,datetime('now'),?)
                        """, (
                            job["id"],
                            url,
                            (urlparse(url).netloc or "").lower(),
                            str(out),
                            "done",
                            "expanded_external_lp",
                            root["id"],
                        ))
                        ok += 1
                        print(f"reference_expand_done job_id={job['id']} idx={idx} url={url}", flush=True)
                    except Exception as e:
                        c.execute("""
                            insert into reference_lp_sources(
                              job_id, source_url, source_domain, local_path, status, note, updated_at, parent_source_id
                            ) values(?,?,?,?,?,?,datetime('now'),?)
                        """, (
                            job["id"],
                            url,
                            (urlparse(url).netloc or "").lower(),
                            "",
                            "error",
                            str(e)[:1000],
                            root["id"],
                        ))
                        print(f"reference_expand_error job_id={job['id']} url={url} err={e}", flush=True)
                if ok > 0:
                    job_done = True
            except Exception as e:
                print(f"reference_expand_root_error job_id={job['id']} root_id={root['id']} err={e}", flush=True)
        if job_done:
            c.execute("""
                update conversation_jobs
                set current_phase='reference_lp_expanded',
                    updated_at=datetime('now')
                where id=?
            """, (job["id"],))
            done += 1
    con.commit()
    con.close()
    print(f"reference_expand_total={done}", flush=True)

def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    run_once(limit)

if __name__ == "__main__":
    main()
