import sqlite3,time,os,subprocess

DB=os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def check():
    try:
        con=sqlite3.connect(DB,timeout=1)
        con.execute("select 1")
        con.close()
        return True
    except:
        return False

fail=0

while True:
    ok=check()
    if not ok:
        fail+=1
    else:
        fail=0

    if fail>=5:
        print("DB LOCK DETECTED")
        os.system("pkill -f openclaw || true")
        break

    time.sleep(5)
