import time
from bots.chat_to_dev.ingest_private_chat_v1 import main as ingest
from bots.chat_to_dev.chat_to_proposal_v1 import main as toprop
from bots.dev_executor_v1 import main as execdev

INTERVAL=30

def main():
    print("daemon start: chat_to_dev")
    while True:
        try:
            ingest()
        except Exception as e:
            print("ingest error",e)
        try:
            toprop()
        except Exception as e:
            print("proposal error",e)
        try:
            execdev()
        except Exception as e:
            print("exec error",e)
        time.sleep(INTERVAL)

if __name__=="__main__":
    main()
