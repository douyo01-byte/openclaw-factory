import time
from bots.spec_decomposer_v1 import run

def main():
    while True:
        try:
            run()
        except Exception:
            pass
        time.sleep(10)

if __name__=="__main__":
    main()
