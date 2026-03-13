import sqlite3,os,time,subprocess,glob

DB=os.environ["DB_PATH"]
LOG_DIR=os.path.expanduser("~/AI/openclaw-factory-daemon/logs")

WATCH_TARGETS=[
"jp.openclaw.supervisor",
"jp.openclaw.spec_refiner_v2",
"jp.openclaw.dev_pr_watcher_v1",
"jp.openclaw.dev_command_executor_v1",
"jp.openclaw.self_healing_v2",
]

def svc_state(label):
    p=subprocess.run(
        ["launchctl","print",f"gui/{os.getuid()}/{label}"],
        capture_output=True,text=True
    )
    if p.returncode != 0:
        return "missing"
    out=p.stdout.lower()
    if "state = running" in out or "state = xpcproxy" in out:
        return "running"
    if "state = spawn scheduled" in out:
        return "scheduled"
    return "other"

def restart(label):
    subprocess.run(
        ["launchctl","kickstart","-k",f"gui/{os.getuid()}/{label}"],
        capture_output=True,text=True
    )

def log_freshness():
    files=glob.glob(os.path.join(LOG_DIR,"*.out"))+glob.glob(os.path.join(LOG_DIR,"*.log"))
    if not files:
        return "no_logs"
    latest=max(os.path.getmtime(f) for f in files)
    age=time.time()-latest
    if age < 300:
        return "fresh"
    if age < 1800:
        return "stale"
    return "old"

while True:
    conn=sqlite3.connect(DB)

    notes=[]
    restarted=[]

    for label in WATCH_TARGETS:
        st=svc_state(label)
        if st in ("missing","other"):
            restart(label)
            restarted.append(label)
            time.sleep(1)
            st=svc_state(label)
        notes.append(f"{label}:{st}")

    freshness=log_freshness()
    notes.append(f"logs:{freshness}")

    if restarted:
        notes.append("restarted:" + ",".join(restarted))

    infra_status="ok"
    if any(":missing" in n for n in notes):
        infra_status="alert"
    elif any(":other" in n for n in notes):
        infra_status="warn"
    elif freshness in ("stale","old","no_logs"):
        infra_status="warn"

    infra_note=" | ".join(notes)

    conn.execute("""
    update dev_proposals
    set infra_status=?,
        infra_note=?
    where status='approved'
    """,(infra_status,infra_note))

    conn.commit()

    print("\n=== Infra Brain v2 ===\n",flush=True)
    print(infra_status,flush=True)
    print(infra_note,flush=True)

    conn.close()
    time.sleep(60)
