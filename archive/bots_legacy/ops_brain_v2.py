import os
import sqlite3
import subprocess
import requests

DB = "data/openclaw.db"
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = "-5293321023"


def n(m):
    if TOKEN:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": m},
        )


def r():
    return subprocess.call(
        ["python", "-m", "bots.command_apply_v1", "--db", DB, "--limit", "50"]
    )


def main():
    c = sqlite3.connect(DB)
    rows = c.execute(
        "select target,updated_at from decisions where decision='adopt' order by updated_at asc"
    ).fetchall()
    c.close()
    for t, ts in rows:
        c2 = sqlite3.connect(DB)
        k = f"{t}|{ts}"
        cur = c2.execute(
            "insert or ignore into executed_decisions(key) values(?)", (k,)
        )
        if cur.rowcount != 1:
            c2.close()
            continue
        c2.commit()
        c2.close()
        n(f"[AutoExecute] {t}")
        rc = r()
        n(f"[Apply] rc={rc}")
        if rc == 0:
            c3 = sqlite3.connect(DB)
            c3.execute(
                "update decisions set decision='done' where target=? and updated_at=?",
                (t, ts),
            )
            c3.commit()
            c3.close()


if __name__ == "__main__":
    main()
