import time
import subprocess

INTERVAL = 600

while True:
    try:
        subprocess.run(
            ["python","-u","bots/project_brain_v4.py"],
            cwd="/Users/doyopc/AI/openclaw-factory-daemon"
        )
    except:
        pass
    time.sleep(INTERVAL)
