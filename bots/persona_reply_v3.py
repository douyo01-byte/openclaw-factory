import os
import sqlite3
import requests
from pathlib import Path
from datetime import datetime

DB = "data/openclaw.db"
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
CHAT_ID = "-5293321023"
ENTRY_GATE_PATH = "prompts/kaikun04_entry_gate.txt"
STARTER_PATH = "~/AI/openclaw-factory-docs/docs/04_KAIKUN04_STARTER.md"

TRIGGER_WORDS = ["作りたい", "実装", "追加", "改善", "強化", "自動化"]


def load_entry_gate():
    try:
        return Path(ENTRY_GATE_PATH).read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def load_starter():
    try:
        return Path(STARTER_PATH.replace("~", str(Path.home()))).read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def build_system_prompt():
    base = "あなたは有能で冷静なAI会社の共同創業者。端的だが人間らしく答える。"
    gate = load_entry_gate()
    starter = load_starter()
    parts = [x for x in [gate, starter, base] if x]
    return "\n\n".join(parts)


def send(msg):
    if TOKEN:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
        )


def llm(text):
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": build_system_prompt(),
                },
                {"role": "user", "content": text},
            ],
        },
    )
    data = r.json()
    if "choices" not in data:
        return f"LLM_ERROR: {data}"
    return data["choices"][0]["message"]["content"]


def auto_register_decision(text):
    for word in TRIGGER_WORDS:
        if word in text:
            conn = sqlite3.connect(DB)
            conn.execute(
                "insert into decisions(target,decision,updated_at) values(?,?,?)",
                (text[:80], "adopt", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            conn.commit()
            conn.close()
            send("🔧 実行候補として登録しました。自動処理に回します。")
            return True
    return False


def main():
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "select id,text from inbox_commands where status='new' order by id asc limit 20"
    ).fetchall()

    for i, text in rows:
        if text.lower().startswith("ok "):
            continue

        if auto_register_decision(text):
            reply = "内容を受領し、実行フェーズへ移行しました。"
        else:
            reply = llm(text)

        send(reply)

        conn.execute("update inbox_commands set status='replied' where id=?", (i,))

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
