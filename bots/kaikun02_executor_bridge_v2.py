import json, os, sqlite3, subprocess
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "reports" / "audit_20260315"
DECISION_FILE = AUDIT / "kaikun02_coo_decision.json"

DB = os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH")
DRY = os.environ.get("KAIKUN02_EXECUTE","0") != "1"

LOG = ROOT / "logs" / "kaikun02_executor_bridge_v2.out"
PYTHON = os.environ.get("KAIKUN02_PYTHON") or "python3"

def log(m):
    LOG.parent.mkdir(exist_ok=True)
    with open(LOG,"a") as f:
        f.write(m+"\n")

def load_decision():
    if not DECISION_FILE.exists():
        return None
    try:
        return json.loads(DECISION_FILE.read_text())
    except:
        return None

def pick_action(decision):
    acts = decision.get("action_templates",[])
    if not acts:
        return None
    return acts[0]

def record_action(action,mode):
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("""
    create table if not exists kaikun02_actions(
        id integer primary key autoincrement,
        proposal_id integer,
        action text,
        mode text,
        created_at text
    )
    """)
    cur.execute(
        "insert into kaikun02_actions(proposal_id,action,mode,created_at) values(?,?,?,?)",
        (action["id"],action["action"],mode,datetime.now(timezone.utc).isoformat())
    )
    con.commit()
    con.close()

def run_refine(pid):
    cmd = [PYTHON,"bots/spec_refiner_v2.py",str(pid)]
    subprocess.run(cmd,cwd=ROOT)

def run_decompose(pid):
    cmd = [PYTHON,"bots/spec_decomposer_v1.py",str(pid)]
    subprocess.run(cmd,cwd=ROOT)

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
                    env["GH_TOKEN"] = line.split("=",1)[1].strip().strip('"')
                if line.startswith("export GITHUB_TOKEN="):
                    env["GITHUB_TOKEN"] = line.split("=",1)[1].strip().strip('"')
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
        log("gate blocked")
        return

    action = pick_action(decision)
    if not action:
        log("no action")
        return

    pid = action["id"]
    act = action["action"]

    log(f"[COO_EXECUTOR] proposal={pid} action={act} dry={DRY}")

    if DRY:
        record_action(action,"dry")
        return

    try:
        if act=="refine_spec":
            run_refine(pid)
        elif act=="decompose_spec":
            run_decompose(pid)
        elif act=="watch_pr":
            run_watch(pid)
        record_action(action,"execute")
    except Exception as e:
        log(f"exec error {e}")

if __name__ == "__main__":
    main()
