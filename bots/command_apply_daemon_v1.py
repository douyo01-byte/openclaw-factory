import time, traceback
from oclibs.tg_api import send_message
from bots.command_apply_v1 import main as apply_main

INTERVAL = 30
FAIL_NOTIFY_THRESHOLD = 5

def main():
    fails = 0
    while True:
        try:
            apply_main()
            fails = 0
        except Exception as e:
            fails += 1
            if fails >= FAIL_NOTIFY_THRESHOLD:
                send_message(f"🔴 command_apply error\n{e}\n{traceback.format_exc()}")
                fails = 0
            time.sleep(30)
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
