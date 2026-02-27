import os, sqlite3
from datetime import datetime
from oclibs.tg_api import send_message

DB_PATH = os.environ.get("OCLAW_DB_PATH", "./data/openclaw.db")
CHAT_ID = os.environ.get("OCLAW_TELEGRAM_CHAT_ID", "-5208829484")

def one(conn, sql):
    cur = conn.execute(sql)
    row = cur.fetchone()
    return row[0] if row else None

def main():
    parts = ["🟢 OpenClaw Alive", f"time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]

    if not os.path.exists(DB_PATH):
        parts.append(f"db: NOT FOUND ({DB_PATH})")
        msg="\n".join(parts)
        chat_id=CHAT_ID
        send_message(chat_id, msg)
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        try: items = one(conn, "SELECT COUNT(*) FROM items")
        except: items = "n/a"
        try: contacts = one(conn, "SELECT COUNT(*) FROM contacts")
        except: contacts = "n/a"
        try: commands = one(conn, "SELECT COUNT(*) FROM inbox_commands")
        except: commands = "n/a"

        parts.append(f"items: {items}")
        parts.append(f"contacts: {contacts}")
        parts.append(f"commands: {commands}")

        try:
            last_meeting = one(conn, "SELECT MAX(created_at) FROM retrospectives")
        except:
            last_meeting = "n/a"
        parts.append(f"last_meeting: {last_meeting}")
        parts.append("status: OK")
    finally:
        conn.close()

    msg="\n".join(parts)
    chat_id=CHAT_ID
    send_message(chat_id, msg)

if __name__ == "__main__":
    main()
