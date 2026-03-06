import os,sqlite3,datetime,requests

DB=os.environ.get("DB_PATH") or "data/openclaw.db"
TOKEN=(os.environ.get("TELEGRAM_REPORT_BOT_TOKEN") or "").strip()
CEO_CHAT_ID=(os.environ.get("CEO_CHAT_ID") or "").strip()

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def main():
    if not TOKEN:
        raise SystemExit("TELEGRAM_REPORT_BOT_TOKEN empty")
    if not CEO_CHAT_ID:
        raise SystemExit("CEO_CHAT_ID empty")

    c=sqlite3.connect(DB,timeout=30)
    c.row_factory=sqlite3.Row
    c.execute("PRAGMA busy_timeout=30000")
    try:
        c.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass

    c.execute("""CREATE TABLE IF NOT EXISTS ceo_hub_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        source_key TEXT NOT NULL,
        title TEXT NOT NULL,
        body TEXT NOT NULL,
        level TEXT NOT NULL DEFAULT 'info',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        sent_at TEXT
    )""")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_ceo_hub_source_key ON ceo_hub_events(source,source_key)")

    rows=c.execute("""
        select id,title,body
        from ceo_hub_events
        where sent_at is null
        order by id asc
        limit 10
    """).fetchall()

    sent=0
    for r in rows:
        text=f"CEO共有\n\n{r['title']}\n\n{r['body']}"
        resp=requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id":CEO_CHAT_ID,"text":text},
            timeout=20,
        )
        resp.raise_for_status()
        c.execute("update ceo_hub_events set sent_at=? where id=?",(now(),int(r["id"])))
        c.commit()
        sent+=1

    c.close()
    print(f"ceo_hub_sent={sent}", flush=True)

if __name__=="__main__":
    main()
