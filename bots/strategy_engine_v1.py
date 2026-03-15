import sqlite3, time, random, traceback, uuid, re

DB="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def slug(x):
    s = re.sub(r'[^a-zA-Z0-9]+', '-', str(x)).strip('-').lower()
    return s or "x"

def get_strategy(conn):
    return conn.execute("""
    select bias_key, weight
    from supply_bias
    where bias_type='reasoning'
    order by weight desc
    """).fetchall()

def choose(rows):
    total = sum(r[1] for r in rows)
    r = random.uniform(0, total)
    upto = 0
    for k, w in rows:
        if upto + w >= r:
            return k
        upto += w
    return rows[0][0]

def write_once(key):
    conn = sqlite3.connect(DB, timeout=30)
    conn.execute("pragma busy_timeout=30000")
    conn.execute("pragma journal_mode=WAL")
    suf = uuid.uuid4().hex[:6]
    title = f"Strategy innovation {key} {suf}"
    branch = f"dev/strategy-{slug(key)}-{suf}"
    conn.execute("""
    insert into dev_proposals
    (title,branch_name,target_system,improvement_type,source_ai,status,dev_stage,created_at)
    values(?,?,?,?,'strategy_engine','approved','idea',datetime('now'))
    """, (title, branch, key, "auto_strategy"))
    conn.commit()
    conn.close()
    print(f"created {title}", flush=True)

def tick():
    conn = sqlite3.connect(DB, timeout=30)
    conn.execute("pragma busy_timeout=30000")
    conn.execute("pragma journal_mode=WAL")
    rows = get_strategy(conn)
    conn.close()
    print(f"strategy_rows={len(rows)} rows={rows[:10]}", flush=True)
    if not rows:
        return
    key = choose(rows)
    print(f"chosen={key}", flush=True)
    for i in range(10):
        try:
            write_once(key)
            return
        except sqlite3.OperationalError as e:
            print(f"retry key={key} i={i} err={e!r}", flush=True)
            time.sleep(1.5)
    raise RuntimeError(f"strategy_write_failed key={key}")

def main():
    print("boot_ok", flush=True)
    while True:
        try:
            tick()
        except Exception as e:
            print(repr(e), flush=True)
            print(traceback.format_exc(), flush=True)
        time.sleep(900)

if __name__=="__main__":
    main()
