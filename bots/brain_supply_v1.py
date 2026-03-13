import time
import subprocess

INTERVAL = 600

while True:
    try:
        subprocess.run(
            ["python", "-u", "bots/project_brain_v4.py"],
            cwd="/Users/doyopc/AI/openclaw-factory-daemon",
            check=False,
        )
    except Exception:
        pass
    time.sleep(INTERVAL)
