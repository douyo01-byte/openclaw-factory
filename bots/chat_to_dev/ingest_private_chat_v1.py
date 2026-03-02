import os
import sqlite3
import requests

DB = os.environ.get("DB_PATH", "data/openclaw.db")
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    offset_row = conn.execute(
        "select ifnull(max(message_id),0) m from tg_private_chat_log"
    ).fetchone()
    offset = offset_row["m"]
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={offset+1}&timeout=0"
    r = requests.get(url, timeout=60).json()
    for u in r.get("result", []):
        m = u.get("message")
        if not m:
            continue
        if m.get("chat", {}).get("type") != "private":
            continue
        mid = m["message_id"]
        text = m.get("text", "")
        conn.execute(
            "insert or ignore into tg_private_chat_log(message_id,text) values(?,?)",
# 既存のコード
for u in r.get("result", []):
    m = u.get("message")
    if not m:
        continue
    if m.get("chat", {}).get("type") != "private":
        continue
    mid = m["message_id"]
    text = m.get("text", "")
    
    # proposal_idが含まれている場合、状態を更新
    if proposal_id is not None and stage == "waiting_answer":
        update_proposal_stage(proposal_id, "answer_received")
    
    # テキストとメッセージIDをデータベースに保存
    conn.execute(
        "insert or ignore into tg_private_chat_log(message_id,text) values(?,?)",
        (mid, text),
    )
conn.commit()            (mid, text),
        )
    conn.commit()


if __name__ == "__main__":
    main()
