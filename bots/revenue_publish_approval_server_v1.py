#!/usr/bin/env python3
import html
import os
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

DB_PATH = os.environ.get(
    "DB_PATH",
    str(Path.home() / "AI/openclaw-factory/data/openclaw.db")
)
HOST = os.environ.get("REVENUE_APPROVAL_HOST", "127.0.0.1")
PORT = int(os.environ.get("REVENUE_APPROVAL_PORT", "8787"))

VALID_STATUS = {"queued", "approved", "published", "rejected"}
VALID_HORIZONS = {"short_term", "mid_term", "long_term"}

def con():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

def has_table(db, name: str) -> bool:
    row = db.execute(
        "select 1 from sqlite_master where type='table' and name=?",
        (name,)
    ).fetchone()
    return row is not None

def table_cols(db, name: str) -> set[str]:
    if not has_table(db, name):
        return set()
    return {r["name"] for r in db.execute(f"pragma table_info({name})").fetchall()}

def ensure_col(db, table: str, col: str, sql: str):
    if col not in table_cols(db, table):
        db.execute(sql)

def ensure_schema(db):
    db.execute("""
        create table if not exists revenue_distribution_publish_queue (
          id integer primary key autoincrement,
          distribution_task_id integer not null unique,
          group_id integer not null,
          experiment_id integer not null,
          variant_key text not null default '',
          distribution_type text not null default '',
          traffic_source text not null default '',
          artifact_path text not null default '',
          candidate_score real not null default 0,
          publish_status text not null default 'queued',
          approval_note text not null default '',
          queued_at text not null default (datetime('now')),
          updated_at text not null default (datetime('now'))
        )
    """)
    db.execute("""
        create table if not exists revenue_memory_patterns (
          id integer primary key autoincrement,
          memory_type text not null,
          pattern text not null,
          horizon_type text not null default 'mid_term',
          economic_summary text not null default '',
          portfolio_summary text not null default '',
          domain_summary text not null default '',
          evidence text not null default '',
          score real not null default 1,
          reuse_count integer not null default 0,
          last_used_at text not null default '',
          created_at text not null default (datetime('now')),
          updated_at text not null default (datetime('now')),
          unique(memory_type, pattern)
        )
    """)
    ensure_col(db, "revenue_memory_patterns", "horizon_type", "alter table revenue_memory_patterns add column horizon_type text not null default 'mid_term'")
    ensure_col(db, "revenue_memory_patterns", "economic_summary", "alter table revenue_memory_patterns add column economic_summary text not null default ''")
    ensure_col(db, "revenue_memory_patterns", "portfolio_summary", "alter table revenue_memory_patterns add column portfolio_summary text not null default ''")
    ensure_col(db, "revenue_memory_patterns", "domain_summary", "alter table revenue_memory_patterns add column domain_summary text not null default ''")

def add_memory(db, memory_type: str, pattern: str, evidence: str, score: float, horizon_type: str = "mid_term", economic_summary: str = "", portfolio_summary: str = "", domain_summary: str = ""):
    pattern = " ".join((pattern or "").split()).strip()[:240]
    if not pattern:
        return
    if horizon_type not in VALID_HORIZONS:
        horizon_type = "mid_term"
    db.execute("""
        insert into revenue_memory_patterns
        (memory_type, pattern, horizon_type, economic_summary, portfolio_summary, domain_summary, evidence, score, reuse_count, created_at, updated_at)
        values
        (?, ?, ?, ?, ?, ?, ?, ?, 0, datetime('now'), datetime('now'))
        on conflict(memory_type, pattern) do update set
          horizon_type=excluded.horizon_type,
          economic_summary=excluded.economic_summary,
          portfolio_summary=excluded.portfolio_summary,
          domain_summary=excluded.domain_summary,
          evidence=excluded.evidence,
          score=max(revenue_memory_patterns.score, excluded.score),
          updated_at=datetime('now')
    """, (memory_type, pattern, horizon_type, economic_summary[:240], portfolio_summary[:240], domain_summary[:240], evidence, score))

def extract_approved_memory(db, queue_id: int):
    row = db.execute("""
        select *
        from revenue_distribution_publish_queue
        where id=?
    """, (queue_id,)).fetchone()
    if not row:
        return
    evidence = f"queue_id={queue_id} type={row['distribution_type']} source={row['traffic_source']}"
    add_memory(db, "winning_distribution", row["distribution_type"], evidence, row["candidate_score"], "long_term")
    add_memory(db, "winning_source", row["traffic_source"], evidence, row["candidate_score"] * 0.8, "mid_term")
    text = ""
    try:
        path = Path(row["artifact_path"])
        if path.exists():
            text = path.read_text(encoding="utf-8")[:240]
    except Exception:
        text = ""
    add_memory(db, "approved_copy", text or row["artifact_path"], evidence, row["candidate_score"] * 0.7, "mid_term")

def update_status(queue_id: int, status: str, note: str = "") -> bool:
    if status not in VALID_STATUS or status == "published":
        return False
    db = con()
    ensure_schema(db)
    cur = db.execute("""
        update revenue_distribution_publish_queue
        set publish_status=?,
            approval_note=?,
            updated_at=datetime('now')
        where id=?
    """, (status, note, queue_id))
    if status == "approved" and cur.rowcount > 0:
        extract_approved_memory(db, queue_id)
    db.commit()
    ok = cur.rowcount > 0
    db.close()
    return ok

def fetch_rows():
    db = con()
    ensure_schema(db)
    rows = db.execute("""
        select *
        from revenue_distribution_publish_queue
        where publish_status in ('queued', 'approved', 'rejected')
        order by
          case publish_status
            when 'queued' then 0
            when 'approved' then 1
            else 2
          end,
          candidate_score desc,
          id asc
    """).fetchall()
    db.close()
    return rows

def render_page(message: str = "") -> str:
    rows = fetch_rows()
    parts = [
        "<!doctype html>",
        "<html><head><meta charset=\"utf-8\"><title>Revenue Publish Approval</title></head><body>",
        "<h1>Revenue Publish Approval</h1>",
        "<p>Localhost only. This updates approval state only; it does not post to SNS.</p>",
    ]
    if message:
        parts.append(f"<p><strong>{html.escape(message)}</strong></p>")
    parts.append("<table border=\"1\" cellspacing=\"0\" cellpadding=\"6\">")
    parts.append("<tr><th>status</th><th>score</th><th>variant</th><th>source</th><th>type</th><th>artifact</th><th>actions</th></tr>")
    for r in rows:
        artifact = Path(r["artifact_path"]).name
        parts.append(
            "<tr>"
            f"<td>{html.escape(r['publish_status'])}</td>"
            f"<td>{float(r['candidate_score'] or 0):.1f}</td>"
            f"<td>{html.escape(r['variant_key'])}</td>"
            f"<td>{html.escape(r['traffic_source'])}</td>"
            f"<td>{html.escape(r['distribution_type'])}</td>"
            f"<td>{html.escape(artifact)}</td>"
            "<td>"
            f"<form method=\"post\" action=\"/approve?id={int(r['id'])}\" style=\"display:inline\"><button>approve</button></form> "
            f"<form method=\"post\" action=\"/reject?id={int(r['id'])}\" style=\"display:inline\"><button>reject</button></form>"
            "</td>"
            "</tr>"
        )
    parts.extend(["</table>", "</body></html>"])
    return "\n".join(parts)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/":
            self.send_response(404)
            self.end_headers()
            return
        body = render_page().encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "text/html; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        queue_id = int((params.get("id") or ["0"])[0] or 0)
        status = "approved" if parsed.path == "/approve" else "rejected" if parsed.path == "/reject" else ""
        ok = update_status(queue_id, status, f"local_approval:{status}")
        body = render_page(f"{status} id={queue_id}" if ok else "not updated").encode("utf-8")
        self.send_response(200 if ok else 400)
        self.send_header("content-type", "text/html; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

def main():
    server = HTTPServer((HOST, PORT), Handler)
    print(f"[revenue_publish_approval_server_v1] http://{HOST}:{PORT}", flush=True)
    server.serve_forever()

if __name__ == "__main__":
    main()
