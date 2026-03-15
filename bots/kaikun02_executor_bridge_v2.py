import json
import os
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db")
DECISION = ROOT / "reports" / "audit_20260315" / "kaikun02_coo_decision.json"
LOG = ROOT / "logs" / "kaikun02_executor_bridge_v2.out"
PYTHON = os.environ.get("KAIKUN02_PYTHON") or "python3"
DRY = str(os.environ.get("KAIKUN02_EXECUTE") or "0").strip() not in ("1", "true", "TRUE", "yes", "on")
COOLDOWN_WATCH = 1800

def log(msg):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(msg.rstrip() + "\n")
    print(msg, flush=True)

def db_conn():
    con = sqlite3.connect(str(DB))
    con.execute("pragma busy_timeout=30000")
    return con

def load_decision():
    if not DECISION.exists():
        return None
    return json.loads(DECISION.read_text(encoding="utf-8"))

def pick_action(decision):
    arr = decision.get("action_templates") or []
    return arr[0] if arr else None

def record_action(action, mode):
    con = db_conn()
    try:
        cols = [r[1] for r in con.execute("pragma table_info(kaikun02_actions)").fetchall()]
        if not cols:
            con.execute("""
            create table if not exists kaikun02_actions(
              id integer primary key autoincrement,
              proposal_id integer,
              action text,
              mode text,
              created_at text
            )
            """)
            cols = [r[1] for r in con.execute("pragma table_info(kaikun02_actions)").fetchall()]
        if "mode" not in cols:
            con.execute("alter table kaikun02_actions add column mode text")
        con.execute(
            "insert into kaikun02_actions(proposal_id,action,mode,created_at) values(?,?,?,?)",
            (
                int(action["id"]),
                str(action["action"]),
                str(mode),
                datetime.now(timezone.utc).isoformat()
            )
        )
        con.commit()
    finally:
        con.close()

def recently_done(action, seconds):
    con = db_conn()
    try:
        row = con.execute(
            """
            select 1
            from kaikun02_actions
            where proposal_id=?
              and action=?
              and mode='execute'
              and created_at >= datetime('now', ?)
            order by id desc
            limit 1
            """,
            (
                int(action["id"]),
                str(action["action"]),
                f"-{int(seconds)} seconds"
            )
        ).fetchone()
        return row is not None
    finally:
        con.close()

def should_skip(action):
    pid = int(action["id"])
    act = str(action["action"])

    con = db_conn()
    try:
        row = con.execute(
            """
            select
              coalesce(spec_stage,''),
              coalesce(pr_status,'')
            from dev_proposals
            where id=?
            """,
            (pid,)
        ).fetchone()
    finally:
        con.close()

    spec_stage = str(row[0] if row else "")
    pr_status = str(row[1] if row else "")

    if act == "refine_spec" and spec_stage == "refined":
        return True, "already_refined"

    if act == "decompose_spec" and spec_stage == "decomposed":
        return True, "already_decomposed"

    if act == "watch_pr":
        if pr_status != "open":
            return True, f"pr_not_open:{pr_status}"
        if recently_done(action, COOLDOWN_WATCH):
            return True, "watch_cooldown"

    return False, ""

def run_refine(pid):
    env = os.environ.copy()
    env["DB_PATH"] = str(DB)
    env["OCLAW_DB_PATH"] = str(DB)
    env["FACTORY_DB_PATH"] = str(DB)
    subprocess.run(
        [PYTHON, "bots/spec_refiner_v2.py", str(pid)],
        cwd=ROOT,
        env=env,
        check=True,
    )

def run_decompose(pid):
    env = os.environ.copy()
    env["DB_PATH"] = str(DB)
    env["OCLAW_DB_PATH"] = str(DB)
    env["FACTORY_DB_PATH"] = str(DB)
    subprocess.run(
        [PYTHON, "bots/spec_decomposer_v1.py", str(pid)],
        cwd=ROOT,
        env=env,
        check=True,
    )

def run_watch(pid):
    env = os.environ.copy()
    env["DB_PATH"] = str(DB)
    env["OCLAW_DB_PATH"] = str(DB)
    env["FACTORY_DB_PATH"] = str(DB)
    gh = (env.get("GH_TOKEN") or env.get("GITHUB_TOKEN") or "").strip()
    if not gh:
        github_env = ROOT / "env" / "github.env"
        if github_env.exists():
            for line in github_env.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("export GH_TOKEN="):
                    env["GH_TOKEN"] = line.split("=", 1)[1].strip().strip('"')
                if line.startswith("export GITHUB_TOKEN="):
                    env["GITHUB_TOKEN"] = line.split("=", 1)[1].strip().strip('"')
    subprocess.run(
        [PYTHON, "bots/dev_pr_watcher_v1.py", str(pid)],
        cwd=ROOT,
        env=env,
        check=True,
    )

def main():
    decision = load_decision()
    if not decision:
        log("no decision")
        return

    if not decision.get("gate_ok"):
        log("health gate blocked")
        return

    action = pick_action(decision)
    if not action:
        return

    pid = int(action["id"])
    act = str(action["action"])

    skip, reason = should_skip(action)
    if skip:
        log(f"[COO_EXECUTOR] skip proposal={pid} action={act} reason={reason} dry={DRY}")
        return

    log(f"[COO_EXECUTOR] proposal={pid} action={act} dry={DRY}")

    if DRY:
        record_action(action, "dry")
        return

    try:
        if act == "refine_spec":
            run_refine(pid)
        elif act == "decompose_spec":
            run_decompose(pid)
        elif act == "watch_pr":
            run_watch(pid)
        else:
            log(f"[COO_EXECUTOR] unknown action={act}")
            return
        record_action(action, "execute")
    except Exception as e:
        log(f"exec error {e}")

if __name__ == "__main__":
    main()
