import os
import time
import traceback
from oclibs.tg_api import send_message
from bots.chat_router_v1 import main as chat_main

CHAT_ID = os.environ.get("OCLAW_TELEGRAM_CHAT_ID", "")
INTERVAL = int(os.environ.get("OCLAW_CHAT_INTERVAL_SEC", "5"))
FAIL_NOTIFY_THRESHOLD = int(os.environ.get("OCLAW_CHAT_FAIL_NOTIFY_THRESHOLD", "5"))

def main():
    fails = 0
    while True:
        try:
            chat_main()
            fails = 0
        except Exception as e:
            fails += 1
            if CHAT_ID and fails >= FAIL_NOTIFY_THRESHOLD:
                send_message(CHAT_ID, f"🔴 chat_router error\n{e}\n{traceback.format_exc(limit=8)}")
                fails = 0
            time.sleep(max(INTERVAL, 5))
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
