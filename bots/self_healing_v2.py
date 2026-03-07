import subprocess,time,os

U=subprocess.check_output(["id","-u"], text=True).strip()
LOG="logs/self_healing_v2.log"

CORE=[
    "jp.openclaw.spec_refiner_v2",
    "jp.openclaw.dev_command_executor_v1",
    "jp.openclaw.dev_executor_daemon_v1",
    "jp.openclaw.dev_pr_watcher_v1",
]
OPS=[
    "jp.openclaw.spec_notify_v1",
]
INGEST_AGENTS=[
    "jp.openclaw.tg_private_ingest_v1",
]

def run(cmd):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True)
    except:
        return ""

def log(msg):
    t=time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG,"a") as f:
        f.write(f"{t} {msg}\n")

def agent_ok(lb):
    s=run(["launchctl","print",f"gui/{U}/{lb}"])
    return ("state = running" in s) or ("state = spawn scheduled" in s)

def restart_agent(lb):
    subprocess.call(
        ["launchctl","kickstart","-k",f"gui/{U}/{lb}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    log(f"{lb} restart")

def tg_poll_ok():
    s=run(["pgrep","-fl","scripts/tg_poll_loop.sh"])
    return "scripts/tg_poll_loop.sh" in s

def restart_tg_poll():
    subprocess.call(
        ["/bin/bash","-lc","pkill -f 'scripts/tg_poll_loop.sh' || true; cd ~/AI/openclaw-factory-daemon || exit 1; nohup bash scripts/tg_poll_loop.sh > logs/tg_poll_loop.nohup.out 2>&1 &"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    log("tg_poll_loop.sh restart")

while True:
    restarted=0
    for lb in CORE:
        if not agent_ok(lb):
            restart_agent(lb)
            restarted=1
    for lb in OPS:
        if not agent_ok(lb):
            restart_agent(lb)
            restarted=1
    if not tg_poll_ok():
        restart_tg_poll()
        restarted=1
    for lb in INGEST_AGENTS:
        if not agent_ok(lb):
            restart_agent(lb)
            restarted=1
    if restarted==0:
        log("ok")
    time.sleep(30)
