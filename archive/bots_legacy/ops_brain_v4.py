import os
import sqlite3
import subprocess
import requests
import time

DB = "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
MODE = os.environ.get("OPS_MODE", "agent").strip().lower()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

def send(m):
    if TOKEN and CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                data={"chat_id": CHAT_ID, "text": m},
                timeout=10,
            )
        except Exception:
            pass

def apply():
    return subprocess.call(
        ["python", "-m", "bots.command_apply_v1", "--db", DB, "--limit", "50"]
    )

def has_table(conn, name):
    row = conn.execute(
        "select 1 from sqlite_master where type='table' and name=?",
        (name,)
    ).fetchone()
    return row is not None

def agent_loop():
    while True:
        c = sqlite3.connect(DB)
        try:
            if not has_table(c, "decisions"):
                c.close()
                time.sleep(10)
                continue

            if not has_table(c, "executed_decisions"):
                c.execute("create table if not exists executed_decisions(key text primary key)")
                c.commit()

            rows = c.execute(
                "select target,updated_at from decisions where decision='adopt' order by updated_at asc"
            ).fetchall()
            c.close()

            for t, ts in rows:
                c2 = sqlite3.connect(DB)
                k = f"{t}|{ts}"
                cur = c2.execute(
                    "insert or ignore into executed_decisions(key) values(?)",
                    (k,)
                )
                if cur.rowcount != 1:
                    c2.close()
                    continue
                c2.commit()
                c2.close()

                send(f"[実行開始] {t}")
                rc = apply()

                c3 = sqlite3.connect(DB)
                if rc == 0:
                    c3.execute(
                        "update decisions set decision='done' where target=? and updated_at=?",
                        (t, ts),
                    )
                    send(f"[完了] {t}")
                else:
                    send(f"[失敗] {t} rc={rc}")
                c3.commit()
                c3.close()

        except Exception as e:
            try:
                send(f"[ops_brain_v4 error] {e}")
            except Exception:
                pass

        time.sleep(10)

def watcher_loop():
    while True:
        subprocess.call(["launchctl", "list"])
        time.sleep(30)

if __name__ == "__main__":
    if MODE == "watch":
        watcher_loop()
    else:
        agent_loop()
