import time, traceback
from oclibs.tg_api import send_message
from bots.tg_inbox_poll_v1 import main as poll_main

SLEEP_SEC = 10
FAIL_NOTIFY_THRESHOLD = 5

def main():
    fails = 0
    while True:
        try:
            poll_main()
            fails = 0
        except Exception as e:
            fails += 1
            if fails >= FAIL_NOTIFY_THRESHOLD:
                send_message(f"🔴 tg_poll error\n{e}\n{traceback.format_exc()}")
                fails = 0
            time.sleep(10)
        time.sleep(SLEEP_SEC)

if __name__ == "__main__":
    main()
