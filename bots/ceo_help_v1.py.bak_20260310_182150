import os,sqlite3,datetime,requests

DB=os.environ.get("DB_PATH") or "data/openclaw.db"
TOKEN=(os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def conn():
    c=sqlite3.connect(DB,timeout=30)
    c.row_factory=sqlite3.Row
    c.execute("PRAGMA busy_timeout=30000")
    try:
        c.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass
    return c

def tg_send(chat_id,text):
    r=requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id":str(chat_id),"text":text},
        timeout=20,
    )
    r.raise_for_status()

def help_text():
    return "\n".join([
        "OpenClaw CEO Command Help",
        "",
        "/company",
        "会社の現在状況を表示",
        "",
        "/meeting <議題>",
        "AI会議を実行",
        "",
        "/help",
        "この一覧を表示",
    ])

def run_once():
    done=0
    with conn() as c:
        rows=c.execute("""
            select id,chat_id,text
            from inbox_commands
            where coalesce(processed,0)=0
              and trim(coalesce(text,''))='/help'
            order by id asc
            limit 5
        """).fetchall()
        for r in rows:
            try:
                tg_send(r["chat_id"], help_text())
                c.execute(
                    "update inbox_commands set processed=1,status='help_done',applied_at=? where id=?",
                    (now(), int(r["id"]))
                )
            except Exception as e:
                c.execute(
                    "update inbox_commands set status='help_error', error=?, applied_at=? where id=?",
                    (repr(e), now(), int(r["id"]))
                )
            c.commit()
            done+=1
    print(f"help_done={done}", flush=True)

if __name__=="__main__":
    run_once()
