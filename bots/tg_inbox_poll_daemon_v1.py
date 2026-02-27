import os, time, traceback
from oclibs.tg_api import send_message
from bots.tg_inbox_poll_v1 import main as poll_main

CHAT_ID = os.environ.get("OCLAW_TELEGRAM_CHAT_ID", "-5208829484")
SLEEP_SEC = int(os.environ.get("OCLAW_POLL_INTERVAL_SEC", "10"))
FAIL_NOTIFY_THRESHOLD = int(os.environ.get("OCLAW_POLL_FAIL_NOTIFY_THRESHOLD", "5"))

def main():
    print('daemon start: tg_poll')
    fails = 0
    while True:
        last_tick = 0
        try:
            poll_main()
            fails = 0
        except Exception as e:
            fails += 1
            if fails >= FAIL_NOTIFY_THRESHOLD:
                send_message(CHAT_ID, f"🔴 tg_poll error\n{e}\n{traceback.format_exc(limit=8)}")
                fails = 0
            time.sleep(max(SLEEP_SEC, 10))
        time.sleep(SLEEP_SEC)

if __name__ == "__main__":
    main()
