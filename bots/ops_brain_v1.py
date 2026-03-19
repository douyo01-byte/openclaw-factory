import os
import json
import time
import socket
import sqlite3
import subprocess
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
MODE = os.environ.get("OPS_BRAIN_MODE", "agent").strip().lower()
HOST = os.environ.get("OPS_BRAIN_HOST", "127.0.0.1").strip()
PORT = int(os.environ.get("OPS_BRAIN_PORT", "8787"))
WATCH_INTERVAL = int(os.environ.get("OPS_BRAIN_INTERVAL", "30"))
WATCHER_TARGETS = [x.strip() for x in os.environ.get("OPS_WATCHER_TARGETS", "http://127.0.0.1:8787/health").split(",") if x.strip()]
WATCHER_RESTART_LABELS = [x.strip() for x in os.environ.get("OPS_WATCHER_RESTART_LABELS", "jp.openclaw.ops_brain_agent_v1").split(",") if x.strip()]
AUTH_TOKEN = os.environ.get("OPS_BRAIN_TOKEN", "").strip()

def db():
    conn = sqlite3.connect(DB, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("pragma busy_timeout=30000")
    try:
        conn.execute("pragma journal_mode=WAL")
    except Exception:
        pass
    return conn

def sh(cmd):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return r.returncode, r.stdout.strip()

def local_services():
    code, out = sh(["launchctl", "list"])
    rows = []
    if code != 0:
        return rows
    for line in out.splitlines():
        if "jp.openclaw." not in line:
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        pid, status, label = parts[0], parts[1], parts[2]
        rows.append({
            "label": label,
            "pid": None if pid == "-" else pid,
            "status": status,
            "running": pid != "-"
        })
    return rows

def write_event(kind, body):
    try:
        conn = db()
        conn.execute("""
        create table if not exists ops_watcher_events(
          id integer primary key autoincrement,
          kind text,
          body text,
          created_at text default (datetime('now'))
        )
        """)
        conn.execute(
            "insert into ops_watcher_events(kind, body) values(?,?)",
            (kind, json.dumps(body, ensure_ascii=False))
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

def agent_health():
    services = local_services()
    running = sum(1 for x in services if x["running"])
    return {
        "ok": True,
        "mode": "agent",
        "host": socket.gethostname(),
        "service_count": len(services),
        "running_count": running,
        "services": services[:50],
        "ts": int(time.time())
    }

def plist_path_for_label(label):
    return os.path.expanduser(f"~/Library/LaunchAgents/{label}.plist")

def restart_label(label):
    if not label.startswith("jp.openclaw."):
        return {"ok": False, "error": "invalid_label"}
    domain = f"gui/{os.getuid()}/{label}"
    code, out = sh(["launchctl", "print", domain])
    service_exists = code == 0
    if service_exists:
        code, out = sh(["launchctl", "kickstart", "-k", domain])
        ok = code == 0
        body = {"ok": ok, "label": label, "mode": "kickstart", "output": out[-1000:]}
        write_event("restart", body)
        return body
    pl = plist_path_for_label(label)
    if not os.path.exists(pl):
        body = {"ok": False, "label": label, "mode": "bootstrap", "error": "plist_not_found", "plist": pl}
        write_event("restart", body)
        return body
    sh(["launchctl", "bootout", f"gui/{os.getuid()}", pl])
    code1, out1 = sh(["launchctl", "bootstrap", f"gui/{os.getuid()}", pl])
    code2, out2 = sh(["launchctl", "enable", domain])
    code3, out3 = sh(["launchctl", "kickstart", "-k", domain])
    ok = code1 == 0 and code3 == 0
    body = {
        "ok": ok,
        "label": label,
        "mode": "bootstrap",
        "bootstrap_output": out1[-1000:],
        "enable_output": out2[-1000:],
        "kickstart_output": out3[-1000:]
    }
    write_event("restart", body)
    return body

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        b = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _auth_ok(self):
        if not AUTH_TOKEN:
            return True
        return self.headers.get("X-Ops-Token", "") == AUTH_TOKEN

    def do_GET(self):
        p = urlparse(self.path)
        if p.path == "/health":
            self._send(200, agent_health())
            return
        if p.path == "/meta":
            self._send(200, {"ok": True, "mode": MODE, "host": socket.gethostname(), "ts": int(time.time())})
            return
        self._send(404, {"ok": False, "error": "not_found"})

    def do_POST(self):
        if not self._auth_ok():
            self._send(401, {"ok": False, "error": "unauthorized"})
            return
        p = urlparse(self.path)
        if p.path == "/restart":
            q = parse_qs(p.query)
            label = (q.get("label") or [""])[0].strip()
            self._send(200, restart_label(label))
            return
        self._send(404, {"ok": False, "error": "not_found"})

    def log_message(self, format, *args):
        return

def run_agent():
    srv = HTTPServer((HOST, PORT), Handler)
    print(f"ops_brain_v1 agent listening on {HOST}:{PORT}", flush=True)
    srv.serve_forever()

def fetch_json(url):
    req = urllib.request.Request(url, headers={"X-Ops-Token": AUTH_TOKEN} if AUTH_TOKEN else {})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))

def post_json(url):
    req = urllib.request.Request(
        url,
        data=b"",
        method="POST",
        headers={"X-Ops-Token": AUTH_TOKEN} if AUTH_TOKEN else {}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))

def run_watcher():
    print("ops_brain_v1 watcher boot", flush=True)
    while True:
        results = []
        any_failed = False
        for url in WATCHER_TARGETS:
            try:
                data = fetch_json(url)
                ok = bool(data.get("ok"))
                if not ok:
                    any_failed = True
                results.append({
                    "url": url,
                    "ok": ok,
                    "service_count": data.get("service_count", 0),
                    "running_count": data.get("running_count", 0)
                })
            except Exception as e:
                any_failed = True
                results.append({"url": url, "ok": False, "error": repr(e)})
        restarted = []
        if any_failed:
            for label in WATCHER_RESTART_LABELS:
                try:
                    restarted.append(post_json(f"http://{HOST}:{PORT}/restart?label={label}"))
                except Exception as e:
                    restarted.append({"ok": False, "label": label, "error": repr(e)})
        body = {
            "mode": "watcher",
            "results": results,
            "restarted": restarted,
            "ts": int(time.time())
        }
        write_event("watch", body)
        print(json.dumps(body, ensure_ascii=False), flush=True)
        time.sleep(WATCH_INTERVAL)

def run_cli():
    print(json.dumps(agent_health(), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    if MODE == "agent":
        run_agent()
    elif MODE == "watcher":
        run_watcher()
    else:
        run_cli()
