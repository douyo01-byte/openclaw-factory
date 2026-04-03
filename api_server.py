from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import sqlite3

DB = os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db")
API_TOKEN = (os.environ.get("OPENCLAW_API_TOKEN") or "").strip()

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    try:
        c.execute("pragma journal_mode=WAL")
    except Exception:
        pass
    return c

def ensure_schema(c):
    cols = {r["name"] for r in c.execute("pragma table_info(inbox_commands)").fetchall()}
    adds = {
        "router_status": "alter table inbox_commands add column router_status text default ''",
        "router_target": "alter table inbox_commands add column router_target text default ''",
        "router_mode": "alter table inbox_commands add column router_mode text default ''",
        "router_finish_status": "alter table inbox_commands add column router_finish_status text default ''",
        "router_task_id": "alter table inbox_commands add column router_task_id integer default 0",
        "updated_at": "alter table inbox_commands add column updated_at text default ''",
    }
    for k, sql in adds.items():
        if k not in cols:
            c.execute(sql)

class Handler(BaseHTTPRequestHandler):
    def _json(self, code: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"ok": True, "service": "api_server"})
            return
        self._json(404, {"ok": False, "error": "not_found"})

    def do_POST(self):
        if self.path != "/inbox":
            self._json(404, {"ok": False, "error": "not_found"})
            return

        if API_TOKEN:
            auth = (self.headers.get("Authorization") or "").strip()
            if auth != f"Bearer {API_TOKEN}":
                self._json(401, {"ok": False, "error": "unauthorized"})
                return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            data = {}

        text = str(data.get("text", "")).strip()
        source = str(data.get("source", "n8n")).strip() or "n8n"

        if not text:
            self._json(400, {"ok": False, "error": "empty_text"})
            return

        with conn() as c:
            ensure_schema(c)
            c.execute(
                """
                insert into inbox_commands(
                    source, text, status, created_at, updated_at,
                    router_status, router_target, router_mode, router_finish_status, router_task_id
                )
                values(?, ?, 'new', datetime('now'), datetime('now'), '', '', '', '', 0)
                """,
                (source, text),
            )
            inbox_id = int(c.execute("select last_insert_rowid()").fetchone()[0])
            c.commit()

        self._json(200, {"ok": True, "id": inbox_id, "source": source, "text": text})

    def log_message(self, format, *args):
        return

HTTPServer(("127.0.0.1", 5001), Handler).serve_forever()
