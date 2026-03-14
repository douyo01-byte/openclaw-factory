import os
import time
import sqlite3
import datetime
import json
import requests

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
FACTORY_DB = os.environ.get("FACTORY_DB_PATH") or DB
OPENAI_API_KEY = (os.environ.get("OPENAI_API_KEY") or "").strip()
OPENAI_MODEL = (os.environ.get("OPENAI_MODEL") or "gpt-4o-mini").strip()
TG_TOKEN = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def dconn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    try:
        c.execute("pragma journal_mode=WAL")
    except Exception:
        pass
    return c

def fconn():
    c = sqlite3.connect(FACTORY_DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    try:
        c.execute("pragma journal_mode=WAL")
    except Exception:
        pass
    return c

def tg_send(chat_id, text):
    if not TG_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN empty")
    r = requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        data={"chat_id": str(chat_id), "text": text},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()

def ask_llm(prompt):
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY empty")
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": OPENAI_MODEL,
            "temperature": 0.4,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an executive AI meeting facilitator for OpenClaw. "
                        "Reply in Japanese. Keep it concrete and short. "
                        "Use sections: 論点, 決定, 保留, 次アクション."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        },
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

def build_context(topic):
    with fconn() as c:
        props = c.execute("""
            select id,title,status,
                   coalesce(spec_stage,'') as spec_stage,
                   coalesce(dev_stage,'') as dev_stage,
                   substr(coalesce(spec,''),1,800) as spec
            from dev_proposals
            order by id desc
            limit 8
        """).fetchall()

        states = []
        try:
            states = c.execute("""
                select proposal_id, stage,
                       substr(coalesce(pending_question,''),1,200) as pending_question,
                       updated_at
                from proposal_state
                order by updated_at desc
                limit 8
            """).fetchall()
        except Exception:
            states = []

    ptxt = []
    for r in props:
        ptxt.append(
            f"id={r['id']} title={r['title']} status={r['status']} "
            f"spec_stage={r['spec_stage']} dev_stage={r['dev_stage']} spec={r['spec']}"
        )

    stxt = []
    for r in states:
        stxt.append(
            f"proposal_id={r['proposal_id']} stage={r['stage']} "
            f"pending={r['pending_question']} updated_at={r['updated_at']}"
        )

    return f"""
topic:
{topic}

latest_dev_proposals:
{chr(10).join(ptxt)}

latest_proposal_states:
{chr(10).join(stxt)}

task:
OpenClaw の短い定例会議メモを作成してください。
必ず以下の形式:
【論点】
・...
【決定】
・...
【保留】
・...
【次アクション】
・...
""".strip()

def save_event(c, title, body):
    try:
        c.execute("""
            insert into ceo_hub_events(title, body, created_at)
            values(?,?,?)
        """, (title, body, now()))
        return
    except Exception:
        pass
    try:
        c.execute("""
            insert into ceo_hub_events(event_type, title, body, created_at)
            values('meeting',?,?,?)
        """, (title, body, now()))
        return
    except Exception:
        pass
    try:
        c.execute("""
            insert into ceo_hub_events(source, source_key, title, body, level, created_at)
            values('meeting_orchestrator_v1', ?, ?, ?, 'info', ?)
        """, (f"meeting:{int(time.time())}", title, body, now()))
        return
    except Exception:
        pass

def run_once():
    done = 0
    with dconn() as c:
        rows = c.execute("""
            select id, chat_id, text
            from inbox_commands
            where coalesce(processed,0)=0
              and trim(coalesce(text,'')) like '/meeting%'
            order by id asc
            limit 5
        """).fetchall()

        for r in rows:
            raw = (r["text"] or "").strip()
            topic = raw[len("/meeting"):].strip() or "OpenClaw の次アクション確認"
            try:
                prompt = build_context(topic)
                out = ask_llm(prompt)
                tg_send(r["chat_id"], out)
                save_event(c, "AI会議結果", out)
                c.execute("""
                    update inbox_commands
                    set processed=1,
                        status='meeting_done',
                        applied_at=?
                    where id=?
                """, (now(), int(r["id"])))
            except Exception as e:
                c.execute("""
                    update inbox_commands
                    set processed=1,
                        status='meeting_error',
                        error=?,
                        applied_at=?
                    where id=?
                """, (repr(e), now(), int(r["id"])))
            c.commit()
            done += 1
    print(f"meeting_done={done}", flush=True)

if __name__ == "__main__":
    while True:
        run_once()
        time.sleep(60)
