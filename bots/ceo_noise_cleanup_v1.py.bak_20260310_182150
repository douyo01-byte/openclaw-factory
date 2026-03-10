import os,sqlite3,datetime

DB=os.environ.get("DB_PATH") or "data/openclaw.db"

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def main():
    c=sqlite3.connect(DB,timeout=30)
    c.row_factory=sqlite3.Row
    c.execute("PRAGMA busy_timeout=30000")
    try:
        c.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass

    rows=c.execute("""
        select id,coalesce(text,'') as text
        from inbox_commands
        where coalesce(processed,0)=0
        order by id asc
        limit 50
    """).fetchall()

    done=0
    for r in rows:
        t=(r["text"] or "").strip().lower()
        if t in ("start","test","ping","probe_1200_xyz","/start"):
            c.execute(
                "update inbox_commands set processed=1,status='skipped',applied_at=? where id=?",
                (now(), int(r["id"]))
            )
            c.commit()
            done+=1
    c.close()
    print(f"noise_skipped={done}", flush=True)

if __name__=="__main__":
    main()
