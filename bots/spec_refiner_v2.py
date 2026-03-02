import os
import sqlite3
import json
import sys
from openai import OpenAI
import requests

env_path = os.path.expanduser("~/AI/openclaw-factory/env/openai.env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if line.startswith("export "):
                k,v=line.replace("export ","").strip().split("=",1)
                os.environ[k]=v

DB = os.environ.get("DB_PATH", "data/openclaw.db")
CHAT_ID = os.environ.get("DEV_CHAT_ID")
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
client = OpenAI()

def tg_send(text):
    if not TOKEN or not CHAT_ID:
        return
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text},
        timeout=20,
    )

def ask_llm(prompt):
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return res.choices[0].message.content

def refine_one(conn, proposal_id):
    row = conn.execute(
        "select title, description from dev_proposals where id=?",
        (proposal_id,),
    ).fetchone()
    if not row:
        return

    title, desc = row

    conv = conn.execute(
        "select role, message from proposal_conversation where proposal_id=? order by id",
        (proposal_id,),
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

    result = ask_llm(prompt)

    try:
        data = json.loads(result)
    except:
        return

    if data.get("status") == "refined":
        spec = data.get("refined_spec", "")

        conn.execute(
            "update dev_proposals set spec_stage='refined' where id=?",
            (proposal_id,),
        )

        conn.execute(
            "insert into proposal_conversation(proposal_id, role, message) values (?, 'assistant', ?)",
            (proposal_id, spec),
        )

        conn.execute(
            "update proposal_state set stage='refined', updated_at=datetime('now') where proposal_id=?",
            (proposal_id,),
        )

        tg_send(f"[Refined #{proposal_id}]\n{spec}")

def run():
    conn = sqlite3.connect(DB)

    if len(sys.argv) > 1:
        refine_one(conn, int(sys.argv[1]))
    else:
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

if spec_stage == "refined":
    decomposed = spec_decompose_v1(spec)
    update_spec_stage(decomposed)


if spec_stage == "refined":
    decomposed = spec_decompose_v1(spec)
    update_spec_stage(decomposed)

