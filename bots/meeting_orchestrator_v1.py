import os,time,sqlite3,datetime,json,requests

DB=os.environ.get("DB_PATH") or "data/openclaw.db"
FACTORY_DB=os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "data/openclaw.db"
OPENAI_API_KEY=(os.environ.get("OPENAI_API_KEY") or "").strip()
OPENAI_MODEL=(os.environ.get("OPENAI_MODEL") or "gpt-4o-mini").strip()
TG_TOKEN=(os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def dconn():
    c=sqlite3.connect(DB,timeout=30)
    c.row_factory=sqlite3.Row
    try:
        c.execute("PRAGMA busy_timeout=30000")
    except Exception:
        pass
    try:
        c.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass
    return c

def fconn():
    c=sqlite3.connect(FACTORY_DB,timeout=30)
    c.row_factory=sqlite3.Row
    try:
        c.execute("PRAGMA busy_timeout=30000")
    except Exception:
        pass
    try:
        c.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass
    return c

def tg_send(chat_id,text):
    if not TG_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN empty")
    r=requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        data={"chat_id":str(chat_id),"text":text},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()

def ask_llm(prompt):
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY empty")
    r=requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization":f"Bearer {OPENAI_API_KEY}",
            "Content-Type":"application/json",
        },
        json={
            "model":OPENAI_MODEL,
            "temperature":0.4,
            "messages":[
                {
                    "role":"system",
                    "content":"You are an executive AI meeting facilitator for OpenClaw Factory. Reply in Japanese. Keep it concrete. Use sections: CEO, Scout, Research, Judge, Dev, NextAction."
                },
                {
                    "role":"user",
                    "content":prompt
                }
            ]
        },
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

def build_context(topic):
    with fconn() as c:
        props=c.execute(
            """
            select id,title,status,coalesce(spec_stage,''),coalesce(dev_stage,''),substr(coalesce(spec,''),1,1200) as spec
            from dev_proposals
            order by id desc
            limit 8
            """
        ).fetchall()
        states=c.execute(
            """
            select proposal_id,stage,substr(coalesce(pending_question,''),1,300) as pending_question,updated_at
            from proposal_state
            order by updated_at desc
            limit 8
            """
        ).fetchall()
    ptxt=[]
    for r in props:
        ptxt.append(f"id={r[0]} title={r[1]} status={r[2]} spec_stage={r[3]} dev_stage={r[4]} spec={r[5]}")
    stxt=[]
    for r in states:
        stxt.append(f"proposal_id={r[0]} stage={r[1]} pending={r[2]} updated_at={r[3]}")
    return f"""
topic:
{topic}

latest_dev_proposals:
{chr(10).join(ptxt)}

latest_proposal_states:
{chr(10).join(stxt)}

task:
Hold a short internal AI meeting for OpenClaw Factory.
Output:
CEO:
Scout:
Research:
Judge:
Dev:
NextAction:
""".strip()

def run_once():
    done=0
    with dconn() as c:
        rows=c.execute(
            """
            select id,chat_id,text
            from inbox_commands
            where coalesce(processed,0)=0
              and trim(coalesce(text,'')) like '/meeting%'
            order by id asc
            limit 5
            """
        ).fetchall()
        for r in rows:
            raw=(r["text"] or "").strip()
            topic=raw[len("/meeting"):].strip() or "OpenClaw の次アクション"
            try:
                prompt=build_context(topic)
                out=ask_llm(prompt)
                tg_send(r["chat_id"], out)
                c.execute(
                    "update inbox_commands set processed=1,status='meeting_done',applied_at=? where id=?",
                    (now(), int(r["id"]))
                )
            except Exception as e:
                c.execute(
                    "update inbox_commands set status='meeting_error', error=?, applied_at=? where id=?",
                    (repr(e), now(), int(r["id"]))
                )
            c.commit()
            done+=1
    print(f"meeting_done={done}", flush=True)

if __name__=="__main__":
    run_once()
