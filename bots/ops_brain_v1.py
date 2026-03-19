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
WATCHER_TARGETS_RAW = os.environ.get(
    "OPS_WATCHER_TARGETS",
    "jp.openclaw.ops_brain_agent_v1|http://127.0.0.1:8787/health|60,"
    "jp.openclaw.dev_pr_automerge_v1||120,"
    "jp.openclaw.db_integrity_watchdog_v1||120,"
    "jp.openclaw.kaikun02_coo_controller_v1||120"
).strip()
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

def now_ts():
    return int(time.time())

def parse_targets():
    out = []
    for raw in WATCHER_TARGETS_RAW.split(","):
        raw = raw.strip()
        if not raw:
            continue
        parts = [x.strip() for x in raw.split("|")]
        label = parts[0] if len(parts) >= 1 else ""
        health_url = parts[1] if len(parts) >= 2 else ""
        cooldown = parts[2] if len(parts) >= 3 and parts[2] else "60"
        policy = parts[3] if len(parts) >= 4 and parts[3] else "required"
        try:
            cooldown = int(cooldown)
        except Exception:
            cooldown = 60
        if label:
            out.append({
                "label": label,
                "health_url": health_url,
                "cooldown": cooldown,
                "policy": policy,
            })
    return out

def service_status(label):
    code, out = sh(["launchctl", "print", f"gui/{os.getuid()}/{label}"])
    if code != 0:
        return {"ok": False, "label": label, "exists": False, "running": False, "raw": out[-500:]}
    running = "state = running" in out
    return {"ok": running, "label": label, "exists": True, "running": running, "raw": out[-500:]}

def recent_restart_blocked(label, cooldown):
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
        row = conn.execute(
            """
            select cast(strftime('%s','now') - strftime('%s', created_at) as integer)
            from ops_watcher_events
            where kind='restart'
              and json_extract(body, '$.label') = ?
              and json_extract(body, '$.ok') = 1
            order by id desc
            limit 1
            """,
            (label,)
        ).fetchone()
        conn.close()
        if not row or row[0] is None:
            return False
        return int(row[0]) < int(cooldown)
    except Exception:
        return False

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

    plist = os.path.expanduser(f"~/Library/LaunchAgents/{label}.plist")
    mode = "kickstart"
    bootstrap_output = ""
    enable_output = ""
    kickstart_output = ""

    st0 = service_status(label)

    if not st0["exists"] and os.path.exists(plist):
        mode = "bootstrap"
        c1, o1 = sh(["launchctl", "bootstrap", f"gui/{os.getuid()}", plist])
        bootstrap_output = o1[-1000:]
        c2, o2 = sh(["launchctl", "enable", f"gui/{os.getuid()}/{label}"])
        enable_output = o2[-1000:]
        c3, o3 = sh(["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/{label}"])
        kickstart_output = o3[-1000:]
        ok = c3 == 0
    else:
        c3, o3 = sh(["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/{label}"])
        kickstart_output = o3[-1000:]
        ok = c3 == 0

    time.sleep(3)
    st1 = service_status(label)

    if ok and st1["running"]:
        restart_result = "running_restored"
    elif ok and st1["exists"]:
        restart_result = "bootstrapped_only"
    else:
        restart_result = "failed"

    body = {
        "ok": ok and st1["exists"],
        "label": label,
        "mode": mode,
        "restart_result": restart_result,
        "service_exists_after": st1["exists"],
        "service_running_after": st1["running"],
        "bootstrap_output": bootstrap_output,
        "enable_output": enable_output,
        "kickstart_output": kickstart_output,
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
    targets = parse_targets()
    while True:
        results = []
        restarted = []
        for t in targets:
            label = t["label"]
            health_url = t["health_url"]
            cooldown = t["cooldown"]
            policy = t.get("policy", "required")
            item = {"label": label, "health_url": health_url, "cooldown": cooldown, "policy": policy}
            failed = False
            if health_url:
                try:
                    data = fetch_json(health_url)
                    ok = bool(data.get("ok"))
                    item["health_ok"] = ok
                    item["service_count"] = data.get("service_count", 0)
                    item["running_count"] = data.get("running_count", 0)
                    if not ok:
                        failed = True
                except Exception as e:
                    item["health_ok"] = False
                    item["health_error"] = repr(e)
                    failed = True
            st = service_status(label)
            item["service_exists"] = st["exists"]
            item["service_running"] = st["running"]

            if policy == "required":
                if not st["running"]:
                    failed = True
            elif policy == "optional":
                item["optional_stopped"] = not st["running"]
            elif policy == "observe":
                item["observed_stopped"] = not st["running"]

            if failed and policy == "required":
                if recent_restart_blocked(label, cooldown):
                    restarted.append({"ok": False, "label": label, "blocked": "cooldown"})
                else:
                    try:
                        restarted.append(restart_label(label))
                    except Exception as e:
                        restarted.append({"ok": False, "label": label, "error": repr(e)})
            results.append(item)
        body = {
            "mode": "watcher",
            "results": results,
            "restarted": restarted,
            "ts": now_ts()
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
