import time
from apply_spec_answers_v1 import tick_once

def main():
    while True:
        try:
            tick_once()
        except Exception as e:
            print("ERR", repr(e))
        time.sleep(2)

if __name__=="__main__":
    main()
