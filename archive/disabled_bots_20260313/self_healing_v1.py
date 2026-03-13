import subprocess,time

U=subprocess.check_output(["id","-u"], text=True).strip()
LOG="logs/self_healing_v1.log"
AGENTS=[
    "jp.openclaw.spec_refiner_v2",
    "jp.openclaw.dev_command_executor_v1",
    "jp.openclaw.dev_executor_daemon_v1",
    "jp.openclaw.dev_pr_watcher_v1",
]

def state(lb):
    try:
        return subprocess.check_output(
            ["launchctl","print",f"gui/{U}/{lb}"],
            stderr=subprocess.DEVNULL,
            text=True
        )
    except:
        return ""

def restart(lb):
    subprocess.call(
        ["launchctl","kickstart","-k",f"gui/{U}/{lb}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def log(msg):
    t=time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG,"a") as f:
        f.write(f"{t} {msg}\n")

while True:
    for lb in AGENTS:
        s=state(lb)
        ok=("state = running" in s) or ("state = spawn scheduled" in s)
        if not ok:
            restart(lb)
            log(f"{lb} restart")
    time.sleep(30)
