import os
import sqlite3
from bots.llm_engine import ask

DB = os.environ.get("DB_PATH", "data/openclaw.db")
CHAT_ID = os.environ.get("DEV_CHAT_ID")
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

import requests

def tg_send(text):
    if not TOKEN or not CHAT_ID:
        return
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text},
        timeout=20
    )

def refine_one(conn, proposal_id):
    st = conn.execute("select stage from proposal_state where proposal_id=?", (proposal_id,)).fetchone()
    stage = st[0] if st else None

    row = conn.execute(
        "select title, description from dev_proposals where id=?",
        (proposal_id,)
    ).fetchone()

    if not row:
        return

    title, desc = row

    prompt = f"""
You are refining a software development proposal.

Title:
{title}

Description:
{desc}

If unclear, generate clarifying questions in JSON:
{{
  "status": "questions",
  "questions": ["Q1", "Q2"]
}}

If clear, return:
{{
  "status": "refined",
  "refined_spec": "Detailed refined specification"
}}
"""

    result = ask(prompt)

    import json
    try:
        data = json.loads(result)
    except:
        return

    if data.get("status") == "questions" and stage != 'answer_received':
        questions = "\n".join(data.get("questions", []))

        conn.execute("""
            insert or replace into proposal_state
            (proposal_id, stage, pending_question)
            values (?, 'waiting_answer', ?)
        """, (proposal_id, questions))

        tg_send(f"[Spec Question #{proposal_id}]\n{questions}")

    elif data.get("status") == "refined":
        spec = data.get("refined_spec", "")

        conn.execute(
            "update dev_proposals set spec_stage='refined' where id=?",
            (proposal_id,)
        )

        conn.execute("""
            insert into proposal_conversation
            (proposal_id, role, message)
            values (?, 'assistant', ?)
        """, (proposal_id, spec))

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
