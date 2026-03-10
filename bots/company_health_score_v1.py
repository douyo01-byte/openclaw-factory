import json, os, sqlite3, subprocess, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
OBS = ROOT / "obs"
OBS.mkdir(parents=True, exist_ok=True)

CHECKS = {
    "autonomous_dev_loop": 20,
    "batch_executor_stability": 10,
    "ranking_discussion_refinement": 10,
    "learning_pattern": 10,
    "kpi_company_health": 10,
    "docs_automation": 10,
    "supply_separation": 10,
    "notification_cleanup": 5,
    "kaikun02_conversation": 5,
    "burnin_72h": 10,
}

def detect_db():
    cands = []
    if os.environ.get("DB_PATH"):
        cands.append(Path(os.environ["DB_PATH"]))
    cands += [
        ROOT / "data" / "openclaw.db",
        ROOT / "data" / "openclaw_daemon.db",
        Path("/Users/doyopc/AI/openclaw-factory/data/openclaw.db"),
        ROOT / "data" / "openclaw",
    ]
    for p in cands:
        if p.exists():
            return p
    return None

def table_exists(conn, name):
    cur = conn.execute("select 1 from sqlite_master where type='table' and name=?", (name,))
    return cur.fetchone() is not None

def launchctl_state(label: str):
    try:
        r = subprocess.run(["launchctl", "print", f"gui/{os.getuid()}/{label}"], capture_output=True, text=True, timeout=15)
        txt = (r.stdout or "") + "\n" + (r.stderr or "")
        if "state = running" in txt:
            return "running"
        if "state = spawn scheduled" in txt:
            return "spawn scheduled"
        if "state = not running" in txt:
            return "not running"
        return "missing"
    except Exception:
        return "missing"

def log_recent(name, sec):
    p = LOGS / name
    return p.exists() and (time.time() - p.stat().st_mtime) <= sec

def main():
    db = detect_db()
    conn = sqlite3.connect(str(db)) if db and db.exists() else None

    detail = {}
    score = 0

    ok_dev_loop = all([
        launchctl_state("jp.openclaw.dev_command_executor_v1") in ("running", "spawn scheduled"),
        launchctl_state("jp.openclaw.dev_pr_watcher_v1") in ("running", "spawn scheduled"),
        launchctl_state("jp.openclaw.dev_pr_automerge_v1") in ("running", "spawn scheduled"),
    ])
    detail["autonomous_dev_loop"] = {"max": 20, "score": 20 if ok_dev_loop else 0}
    score += detail["autonomous_dev_loop"]["score"]

    ok_batch = log_recent("dev_command_executor_v1.out", 3600) and log_recent("dev_pr_watcher_v1.out", 3600)
    detail["batch_executor_stability"] = {"max": 10, "score": 10 if ok_batch else 0}
    score += detail["batch_executor_stability"]["score"]

    rr = 0
    if (ROOT / "bots" / "proposal_ranking_v1.py").exists() or (ROOT / "bots" / "proposal_ranking_v1.py.bak_20260310_121755").exists():
        rr += 4
    if (ROOT / "bots" / "spec_refiner_v2.py").exists():
        rr += 3
    if table_exists(conn, "proposal_conversation") if conn else False:
        rr += 3
    detail["ranking_discussion_refinement"] = {"max": 10, "score": rr}
    score += rr

    lp = 0
    if (ROOT / "bots" / "learning_pattern_engine_v1.py").exists():
        lp += 4
    if log_recent("ai_employee_ranking_v1.out", 86400):
        lp += 3
    if table_exists(conn, "decision_patterns") if conn else False:
        lp += 3
    detail["learning_pattern"] = {"max": 10, "score": lp}
    score += lp

    kh = 0
    if (ROOT / "bots" / "db_integrity_check_v1.py").exists():
        kh += 4
    if (ROOT / "bots" / "watchdog_v1.py").exists():
        kh += 3
    if launchctl_state("jp.openclaw.ceo_dashboard") in ("running", "spawn scheduled"):
        kh += 3
    detail["kpi_company_health"] = {"max": 10, "score": kh}
    score += kh

    da = 0
    if launchctl_state("jp.openclaw.docs_sync_v1") in ("running", "spawn scheduled", "not running"):
        da += 5
    if (ROOT / "docs" / "observability" / "db_integrity.sql").exists():
        da += 3
    if (ROOT / "docs" / "observability" / "supply_adoption.sql").exists():
        da += 2
    detail["docs_automation"] = {"max": 10, "score": da}
    score += da

    ss = 0
    for fn in [
        "innovation_engine_v1.py",
        "code_supply_engine_v1.py",
        "brain_supply_engine_v1.py",
        "ops_supply_engine_v1.py",
    ]:
        if (ROOT / "bots" / fn).exists():
            ss += 2
    ss = min(ss, 10)
    detail["supply_separation"] = {"max": 10, "score": ss}
    score += ss

    nc = 0
    if (ROOT / "bots" / "watchdog_v1.py").exists():
        nc += 2
    if (ROOT / "bots" / "db_integrity_check_v1.py").exists():
        nc += 2
    if log_recent("tg_poll.log", 3600):
        nc += 1
    detail["notification_cleanup"] = {"max": 5, "score": nc}
    score += nc

    kc = 0
    if (ROOT / "bots" / "chat_router_v1.py").exists():
        kc += 2
    if (ROOT / "bots" / "ai_ceo_engine_v1.py").exists():
        kc += 2
    if table_exists(conn, "inbox_commands") if conn else False:
        kc += 1
    detail["kaikun02_conversation"] = {"max": 5, "score": kc}
    score += kc

    bi = 0
    if (ROOT / "bots" / "watchdog_v1.py").exists():
        bi += 4
    if (ROOT / "bots" / "db_integrity_check_v1.py").exists():
        bi += 3
    if (ROOT / "bots" / "supply_adoption_metrics_v1.py").exists():
        bi += 3
    detail["burnin_72h"] = {"max": 10, "score": bi}
    score += bi

    out = {
        "generated_at": int(time.time()),
        "db_path": str(db) if db else None,
        "maturity_percent": score,
        "detail": detail,
    }

    (OBS / "company_health_score.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    with (LOGS / "company_health_score_v1.log").open("a", encoding="utf-8") as f:
        f.write(f"[maturity] percent={score}\n")

    if conn:
        conn.close()

if __name__ == "__main__":
    main()
