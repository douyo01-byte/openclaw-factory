import json, os, sqlite3, subprocess, time
from pathlib import Path
from urllib import request, parse

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
OBS = ROOT / "obs"
OBS.mkdir(parents=True, exist_ok=True)

WATCH = {
    "tg_poll_loop": {
        "labels": ["jp.openclaw.tg_poll_loop", "jp.openclaw.tg_poll"],
        "logs": ["tg_poll.log", "tg_poll_heartbeat.log"],
    },
    "dev_command_executor_v1": {
        "labels": ["jp.openclaw.dev_command_executor_v1"],
        "logs": ["dev_command_executor_v1.out", "dev_command_executor_v1.err"],
    },
    "dev_pr_watcher_v1": {
        "labels": ["jp.openclaw.dev_pr_watcher_v1"],
        "logs": ["dev_pr_watcher_v1.out", "dev_pr_watcher_v1.err", "jp.openclaw.dev_pr_watcher_v1.out", "jp.openclaw.dev_pr_watcher_v1.err"],
    },
    "dev_pr_automerge_v1": {
        "labels": ["jp.openclaw.dev_pr_automerge_v1"],
        "logs": ["dev_pr_automerge_v1.out", "dev_pr_automerge_v1.err"],
    },
    "innovation_engine": {
        "labels": ["jp.openclaw.innovation_engine"],
        "logs": ["innovation_engine.out", "innovation_engine.err"],
    },
    "code_supply_engine": {
        "labels": ["jp.openclaw.code_supply_engine_v1", "jp.openclaw.code_supply_engine"],
        "logs": ["code_supply_engine_v1.out", "code_supply_engine_v1.err"],
    },
    "brain_supply_engine": {
        "labels": ["jp.openclaw.brain_supply_engine_v1", "jp.openclaw.brain_supply_engine"],
        "logs": ["brain_supply_engine_v1.out", "brain_supply_engine_v1.err"],
    },
    "ops_supply_engine": {
        "labels": ["jp.openclaw.ops_supply_engine_v1", "jp.openclaw.mainstream_supply_v1", "jp.openclaw.ops_supply_engine"],
        "logs": ["mainstream_supply_v1.out", "mainstream_supply_v1.err"],
    },
    "learning_pattern_engine": {
        "labels": ["jp.openclaw.learning_pattern_engine_v1", "jp.openclaw.ai_employee_ranking_v1"],
        "logs": ["ai_employee_ranking_v1.out"],
        "optional": True,
    },
    "company_dashboard": {
        "labels": ["jp.openclaw.company_dashboard_v1", "jp.openclaw.ceo_dashboard"],
        "logs": ["ceo_dashboard.out", "ceo_dashboard.err", "ceo_dashboard.log"],
        "allow_spawn_scheduled": True,
    },
    "docs_sync": {
        "labels": ["jp.openclaw.docs_sync_v1", "jp.openclaw.docs_sync"],
        "logs": [],
        "optional": True,
        "allow_not_running": True,
    },
}

STALE_SEC = int(os.environ.get("WATCHDOG_STALE_SEC", "900"))
NO_MERGE_SEC = int(os.environ.get("WATCHDOG_NO_MERGE_SEC", "3600"))
NO_PROPOSAL_SEC = int(os.environ.get("WATCHDOG_NO_PROPOSAL_SEC", "3600"))
STATE_PATH = OBS / "watchdog_state.json"

def now():
    return int(time.time())

def launchctl_state(label: str):
    try:
        r = subprocess.run(["launchctl", "print", f"gui/{os.getuid()}/{label}"], capture_output=True, text=True, timeout=15)
        txt = (r.stdout or "") + "\n" + (r.stderr or "")
        if "Could not find service" in txt or "could not find service" in txt:
            return "missing", txt
        for key in ["state = running", "state = spawn scheduled", "state = not running"]:
            if key in txt:
                return key.split("=", 1)[1].strip(), txt
        return "unknown", txt
    except Exception as e:
        return "error", str(e)

def any_label_state(labels):
    found = []
    for x in labels:
        st, txt = launchctl_state(x)
        if st != "missing":
            found.append((x, st, txt))
    if found:
        for x, st, txt in found:
            if st == "running":
                return "running", x, txt
        return found[0][1], found[0][0], found[0][2]
    return "missing", "", ""

def newest_mtime(files):
    mts = []
    for f in files:
        p = LOGS / f
        if p.exists():
            mts.append(int(p.stat().st_mtime))
    return max(mts) if mts else 0

def tg_send(token, chat_id, text):
    if not token or not chat_id or not text:
        return
    data = parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    req = request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    try:
        request.urlopen(req, timeout=20).read()
    except Exception:
        pass

def detect_db():
    cands = []
    if os.environ.get("DB_PATH"):
        cands.append(Path(os.environ["DB_PATH"]))
    cands += [
        ROOT / "data" / "openclaw.db",
        ROOT / "data" / "openclaw_daemon.db",
        ROOT / "data" / "openclaw",
    ]
    for p in cands:
        if p.exists():
            return p
    return None

def table_exists(conn, name):
    cur = conn.execute("select 1 from sqlite_master where type='table' and name=?", (name,))
    return cur.fetchone() is not None

def get_metric_times():
    db = detect_db()
    res = {"last_merge": 0, "last_proposal": 0}
    if not db:
        return res
    try:
        conn = sqlite3.connect(str(db))
        if table_exists(conn, "ceo_hub_events"):
            cols = [r[1] for r in conn.execute("pragma table_info(ceo_hub_events)").fetchall()]
            if {"event_type", "created_at"} <= set(cols):
                x = conn.execute("select max(strftime('%s', created_at)) from ceo_hub_events where event_type in ('merged','merge','pr_merged','learning_result')").fetchone()[0]
                y = conn.execute("select max(strftime('%s', created_at)) from ceo_hub_events where event_type in ('proposal_created','proposal','pr_created')").fetchone()[0]
                res["last_merge"] = int(x or 0)
                res["last_proposal"] = int(y or 0)
        if table_exists(conn, "dev_proposals") and res["last_proposal"] == 0:
            cols = [r[1] for r in conn.execute("pragma table_info(dev_proposals)").fetchall()]
            for col in ("created_at", "updated_at"):
                if col in cols:
                    x = conn.execute(f"select max(strftime('%s', {col})) from dev_proposals").fetchone()[0]
                    res["last_proposal"] = max(res["last_proposal"], int(x or 0))
        conn.close()
    except Exception:
        pass
    return res

def load_state():
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_state(d):
    STATE_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

def main():
    ts = now()
    state = load_state()
    ka01_token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("KAIKUN01_BOT_TOKEN")
    ka01_chat = os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("KAIKUN01_CHAT_ID")
    ka02_token = os.environ.get("CEO_TELEGRAM_BOT_TOKEN") or ka01_token
    ka02_chat = os.environ.get("CEO_CHAT_ID") or os.environ.get("KAIKUN02_CHAT_ID")

    lines = []
    alerts01 = []
    alerts02 = []

    for name, cfg in WATCH.items():
        state_name, matched_label, raw = any_label_state(cfg["labels"])
        mtime = newest_mtime(cfg["logs"])
        stale = (mtime > 0 and ts - mtime > STALE_SEC) or (mtime == 0 and len(cfg["logs"]) > 0)
        optional = bool(cfg.get("optional"))
        allow_spawn_scheduled = bool(cfg.get("allow_spawn_scheduled"))
        allow_not_running = bool(cfg.get("allow_not_running"))

        alive_like = state_name == "running" or (allow_spawn_scheduled and state_name == "spawn scheduled") or (allow_not_running and state_name == "not running")

        if state_name == "missing" and optional:
            lines.append(f"[watchdog] skip_optional process={name}")
            continue

        if alive_like and not stale:
            lines.append(f"[watchdog] ok process={name}")
        elif alive_like and stale:
            age = ts - mtime if mtime else -1
            lines.append(f"[watchdog] stale_log process={name} age_sec={age}")
            alerts01.append(f"⚠ OpenClaw 開発異常\nprocess: {name}\nreason: log stale\nage_sec: {age}")
            alerts02.append(f"⚠ OpenClaw company health\nstale log: {name}\nage_sec: {age}")
        else:
            lines.append(f"[watchdog] dead process={name}")
            alerts01.append(f"⚠ OpenClaw 開発異常\nprocess: {name}\nreason: dead")
            alerts02.append(f"⚠ OpenClaw company health\nprocess stopped: {name}")

    mt = get_metric_times()
    if mt["last_merge"] and ts - mt["last_merge"] > NO_MERGE_SEC:
        mins = (ts - mt["last_merge"]) // 60
        lines.append(f"[watchdog] no_merge_progress minutes={mins}")
        alerts02.append(f"⚠ OpenClaw company health\nmerge progress stopped\ntime: {mins}min")
    if mt["last_proposal"] and ts - mt["last_proposal"] > NO_PROPOSAL_SEC:
        mins = (ts - mt["last_proposal"]) // 60
        lines.append(f"[watchdog] no_proposal_progress minutes={mins}")
        alerts02.append(f"⚠ OpenClaw company health\nproposal rate dropped\ntime: {mins}min")

    out = LOGS / "watchdog_v1.log"
    with out.open("a", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

    cur_key = "\n".join(sorted(set(alerts01 + alerts02)))
    prev_key = state.get("last_alert_key", "")
    if cur_key and cur_key != prev_key:
        if alerts01:
            tg_send(ka01_token, ka01_chat, "\n\n".join(sorted(set(alerts01))[:4]))
        if alerts02:
            tg_send(ka02_token, ka02_chat, "\n\n".join(sorted(set(alerts02))[:4]))
        state["last_alert_key"] = cur_key
        state["last_alert_at"] = ts
    elif not cur_key:
        state["last_alert_key"] = ""

    state["last_run_at"] = ts
    state["last_merge"] = mt["last_merge"]
    state["last_proposal"] = mt["last_proposal"]
    save_state(state)

if __name__ == "__main__":
    main()
