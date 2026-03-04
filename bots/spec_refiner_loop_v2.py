import time
from spec_refiner_v2 import tick_once

def main():
    while True:
        try:
            tick_once()
        except Exception as e:
            print("ERR",repr(e))
        time.sleep(2)

if __name__=="__main__":
    main()
