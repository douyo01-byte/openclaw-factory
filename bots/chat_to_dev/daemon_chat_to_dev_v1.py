import time,traceback
from bots.chat_to_dev.ingest_private_chat_v1 import main as ingest
from bots.chat_to_dev.chat_to_proposal_v1 import main as toprop
from bots.dev_executor_v1 import main as execdev

INTERVAL=30

def main():
    print("daemon start: chat_to_dev")
    while True:
        try:
            ingest()
            toprop()
            execdev()
        except Exception as e:
            print("error",e)
        time.sleep(INTERVAL)

if __name__=="__main__":
    main()
