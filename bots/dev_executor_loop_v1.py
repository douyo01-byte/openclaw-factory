import time
from dev_executor_v1 import main
def run():
    while True:
        try:
            main()
        except SystemExit:
            pass
        except Exception as e:
            print("ERR",repr(e))
        time.sleep(5)
if __name__=="__main__":
    run()
