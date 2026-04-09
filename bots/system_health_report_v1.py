import sqlite3, os, time

DB_PATH = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def run():
    while True:
        c = sqlite3.connect(DB_PATH)
        r = c.execute("""
        select target_bot, status, count(*)
        from router_tasks
        group by target_bot, status
        """).fetchall()
        print("=== system health ===", flush=True)
        for row in r:
            print(row, flush=True)
        c.close()
        time.sleep(60)

if __name__ == "__main__":
    run()
