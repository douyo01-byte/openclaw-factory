import os
import re
import time
import sqlite3
import requests
from datetime import datetime

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
DB = os.environ["DB_PATH"]
API = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

TASK_ID_RE = re.compile(r"\[TASK_ID:(\d+)\]")

def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("pragma journal_mode=WAL")
    c.execute("pragma busy_timeout=5000")
    return c

def ensure_columns(c):
    cols = {r["name"] for r in c.execute("pragma table_info(router_tasks)")}
    if "reply_text" not in cols:
        c.execute("alter table router_tasks add column reply_text text default ''")
    if "sent_message_id" not in cols:
        c.execute("alter table router_tasks add column sent_message_id text default ''")
    cols2 = {r["name"] for r in c.execute("pragma table_info(inbox_commands)")}
    if "router_finish_status" not in cols2:
        c.execute("alter table inbox_commands add column router_finish_status text default ''")
    if "router_task_id" not in cols2:
        c.execute("alter table inbox_commands add column router_task_id integer")
    c.commit()

def insert_chat_log(c, mid, chat_id, text):
    try:
        c.execute(
            "insert into tg_private_chat_log(message_id,chat_id,text) values(?,?,?)",
            (mid, chat_id, text),
        )
    except sqlite3.IntegrityError:
        pass
    except sqlite3.OperationalError:
        pass

def find_task(c, text, reply_to_message_id):
    m = TASK_ID_RE.search(text or "")
    if m:
        row = c.execute(
            "select * from router_tasks where id=?",
            (int(m.group(1)),)
        ).fetchone()
        if row:
            return row

    if reply_to_message_id:
        row = c.execute(
            """
            select *
            from router_tasks
            where cast(coalesce(sent_message_id,'') as text)=?
            order by id desc
            limit 1
            """,
            (str(reply_to_message_id),)
        ).fetchone()
        if row:
            return row

    return None

def apply_reply(c, task_row, text):
    ts = now()
    task_id = task_row["id"]
    source_command_id = task_row["source_command_id"]

    result_text = task_row["result_text"] or ""
    if "reply_received" not in result_text:
        result_text = (result_text + " | reply_received").strip(" |")

    c.execute(
        """
        update router_tasks
        set status='done',
            finished_at=?,
            updated_at=?,
            result_text=?,
            reply_text=?
        where id=?
        """,
        (ts, ts, result_text, text, task_id)
    )

    if source_command_id:
        c.execute(
            """
            update inbox_commands
            set status='done',
                processed=1,
                router_status='routed',
                router_finish_status='applied',
                router_task_id=?,
                updated_at=?
            where id=?
            """,
            (task_id, ts, source_command_id)
        )

    c.commit()

def main():
    print(f"[ingest_private] boot db={DB} token_head={TOKEN[:12]}...", flush=True)
    offset = 0

    while True:
        try:
            r = requests.get(
                API,
                params={"offset": offset + 1, "timeout": 30},
                timeout=35,
            )
            data = r.json()
            rows = data.get("result", [])
            print(f"[ingest_private] polled count={len(rows)} offset={offset}", flush=True)

            with conn() as c:
                ensure_columns(c)

                for u in rows:
                    offset = u["update_id"]
                    m = u.get("message")
                    if not m:
                        continue

                    text = m.get("text", "") or ""
                    mid = m.get("message_id")
                    chat_id = m.get("chat", {}).get("id")
                    reply_to_message_id = (m.get("reply_to_message") or {}).get("message_id")

                    insert_chat_log(c, mid, chat_id, text)

                    task_row = find_task(c, text, reply_to_message_id)
                    if not task_row:
                        continue

                    apply_reply(c, task_row, text)
                    print(f"[ingest_private] applied task_id={task_row['id']} source_command_id={task_row['source_command_id']}", flush=True)

        except Exception as e:
            print(f"[ingest_private] error={e!r}", flush=True)

        time.sleep(2)

if __name__ == "__main__":
    main()
