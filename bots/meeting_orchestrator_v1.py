import os
import time
import sqlite3
import datetime
import requests

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
OPENAI_API_KEY = (os.environ.get("OPENAI_API_KEY") or "").strip()
OPENAI_MODEL = (os.environ.get("OPENAI_MODEL") or "gpt-4o-mini").strip()
TG_TOKEN = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
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
                    "content": "You are an executive AI meeting facilitator for OpenClaw. Reply in concise Japanese. Use sections: 今回の論点 / 決定事項 / 保留事項 / 次の一手."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        },
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

def q(c, sql, args=()):
    row = c.execute(sql, args).fetchone()
    if not row:
        return 0
    v = row[0]
    return 0 if v is None else v

def build_context(topic):
    with conn() as c:
        merged = q(c, "select count(*) from dev_proposals where coalesce(dev_stage,'')='merged'")
        approved = q(c, "select count(*) from dev_proposals where coalesce(status,'')='approved'")
        open_pr = q(c, "select count(*) from dev_proposals where coalesce(pr_status,'')='open'")
        backlog = q(c, """
            select count(*)
            from dev_proposals
            where coalesce(project_decision,'')='execute_now'
              and coalesce(dev_stage,'') not in ('merged','closed')
        """)
        latest = c.execute("""
            select id,title,coalesce(source_ai,''),coalesce(dev_stage,''),coalesce(pr_status,'')
            from dev_proposals
            order by id desc
            limit 8
        """).fetchall()
        cto = c.execute("""
            select id,title,coalesce(status,''),coalesce(project_decision,''),coalesce(dev_stage,''),coalesce(pr_status,'')
            from dev_proposals
            where coalesce(source_ai,'')='cto'
            order by id desc
            limit 5
        """).fetchall()

    latest_lines = []
    for r in latest:
        latest_lines.append(f"id={r[0]} title={r[1]} source_ai={r[2]} dev_stage={r[3]} pr_status={r[4]}")
    cto_lines = []
    for r in cto:
        cto_lines.append(f"id={r[0]} title={r[1]} status={r[2]} decision={r[3]} dev_stage={r[4]} pr_status={r[5]}")

    return f"""
topic:
{topic}

company_snapshot:
merged={merged}
approved={approved}
open_pr={open_pr}
backlog={backlog}

latest_dev_proposals:
{chr(10).join(latest_lines) if latest_lines else 'none'}

cto_proposals:
{chr(10).join(cto_lines) if cto_lines else 'none'}

短い定例会議メモを作成してください。
必ず次の形式:
【今回の論点】
・...
【決定事項】
・...
【保留事項】
・...
【次の一手】
・...
""".strip()

def run_once():
    done = 0
    with conn() as c:
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
            topic = raw[len("/meeting"):].strip() or "OpenClaw の 状況確認"
            try:
                out = ask_llm(build_context(topic))
                tg_send(r["chat_id"], out)
                c.execute("""
                    insert into ceo_hub_events(event_type,title,body,proposal_id,pr_url,created_at,sent_at)
                    values(?,?,?,?,?,?,?)
                """, (
                    "meeting",
                    f"AI会議: {topic[:80]}",
                    out,
                    None,
                    "",
                    now(),
                    now(),
                ))
                c.execute("""
                    update inbox_commands
                    set processed=1,status='meeting_done',applied_at=?,error=''
                    where id=?
                """, (now(), int(r["id"])))
                c.commit()
                done += 1
            except Exception as e:
                c.execute("""
                    update inbox_commands
                    set processed=1,status='meeting_error',applied_at=?,error=?
                    where id=?
                """, (now(), repr(e), int(r["id"])))
                c.commit()
    print(f"meeting_done={done}", flush=True)

if __name__ == "__main__":
    while True:
        try:
            run_once()
        except Exception as e:
            print(f"meeting_error={e!r}", flush=True)
        time.sleep(20)
