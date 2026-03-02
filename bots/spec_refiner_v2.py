import os
import sqlite3
import json
from bots.llm_engine import ask
import requests

DB = os.environ.get("DB_PATH", "data/openclaw.db")
CHAT_ID = os.environ.get("DEV_CHAT_ID")
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

def tg_send(text):
    if not TOKEN or not CHAT_ID:
        return
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text},
        timeout=20
    )

def refine_one(conn, proposal_id):
    row = conn.execute(
        "select title, description from dev_proposals where id=?",
        (proposal_id,)
    ).fetchone()
    if not row:
        return

    title, desc = row

    conv = conn.execute(
        "select role, message from proposal_conversation where proposal_id=? order by id",
        (proposal_id,)
    ).fetchall()

    history = "\n".join([f"{r[0]}: {r[1]}" for r in conv])

    prompt = f"""
Return ONLY JSON.
Always return:
{{
  "status": "refined",
  "refined_spec": "Full detailed final specification including all assumptions."
}}

Title:
{title}

Description:
{desc}

Conversation:
{history}
"""

    result = ask(prompt)

    try:
        data = json.loads(result)
    except:
        return

    if data.get("status") == "refined":
        spec = data.get("refined_spec", "")

        conn.execute(
            "update dev_proposals set spec_stage='refined' where id=?",
            (proposal_id,)
        )

        conn.execute(
            "insert into proposal_conversation(proposal_id, role, message) values (?, 'assistant', ?)",
            (proposal_id, spec)
        )

        conn.execute(
            "update proposal_state set stage='refined', updated_at=datetime('now') where proposal_id=?",
            (proposal_id,)
        )

        tg_send(f"[Refined #{proposal_id}]\n{spec}")

def run():
    conn = sqlite3.connect(DB)

    rows = conn.execute("""
        select id from dev_proposals
        where status='approved'
        and (
            spec_stage is null
            or spec_stage='raw'
            or id in (
                select proposal_id
                from proposal_state
                where stage='answer_received'
            )
        )
    """).fetchall()

    for r in rows:
        refine_one(conn, r[0])

    conn.commit()
    conn.close()

if __name__ == "__main__":
    run()
