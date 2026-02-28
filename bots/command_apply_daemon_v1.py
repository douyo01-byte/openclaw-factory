import os, time, traceback
from oclibs.tg_api import send_message
from bots.command_apply_v1 import main as apply_main

CHAT_ID = os.environ.get("OCLAW_TELEGRAM_CHAT_ID", "-5208829484")
INTERVAL = int(os.environ.get("OCLAW_APPLY_INTERVAL_SEC", "30"))
FAIL_NOTIFY_THRESHOLD = int(os.environ.get("OCLAW_APPLY_FAIL_NOTIFY_THRESHOLD", "5"))

def main():
    print('daemon start: command_apply')
    fails = 0
    while True:
        last_tick = 0
        try:
            apply_main()
            fails = 0
        except Exception as e:
            fails += 1
            if fails >= FAIL_NOTIFY_THRESHOLD:
                send_message(CHAT_ID, f"🔴 command_apply error\n{e}\n{traceback.format_exc(limit=8)}")
                fails = 0
            time.sleep(max(INTERVAL, 30))
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
