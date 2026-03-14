import os
import sqlite3
import time
import urllib.parse
import urllib.request

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
BOT = (os.environ.get("TELEGRAM_CEO_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
CHAT = (os.environ.get("TELEGRAM_CEO_CHAT_ID") or os.environ.get("CEO_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID") or "").strip()

def tg(text: str):
    if not BOT or not CHAT:
        raise RuntimeError("missing_token_or_chat")
    data = urllib.parse.urlencode({"chat_id": CHAT, "text": text}).encode()
    url = f"https://api.telegram.org/bot{BOT}/sendMessage"
    with urllib.request.urlopen(url, data=data, timeout=20) as r:
        return r.read().decode("utf-8", errors="ignore")

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    return c

def ensure_cols(c):
    cols = [r[1] for r in c.execute("pragma table_info(dev_proposals)").fetchall()]
    if "notified_at" not in cols:
        c.execute("alter table dev_proposals add column notified_at text")
    if "notified_msg_id" not in cols:
        c.execute("alter table dev_proposals add column notified_msg_id text")
    c.commit()

def build_msg(r):
    pid = r["id"]
    title = (r["title"] or "").strip()
    desc = (r["description"] or "").strip()
    src = (r["source_ai"] or "").strip() or "ai"
    target = (r["target_system"] or "").strip() or "core"
    kind = (r["improvement_type"] or "").strip() or "automation"
    status = (r["status"] or "").strip()
    decision = (r["project_decision"] or "").strip()
    dev_stage = (r["dev_stage"] or "").strip()
    lines = []
    lines.append("📨 OpenClaw AI→CEO 提案")
    lines.append(f"ID: #{pid}")
    lines.append(f"件名: {title}")
    lines.append(f"提案元: {src}")
    lines.append(f"対象: {target}")
    lines.append(f"種別: {kind}")
    lines.append(f"状態: {status} / {decision} / {dev_stage}")
    if desc:
        short = " ".join(x.strip() for x in desc.replace("\r", "\n").split("\n") if x.strip())[:300]
        lines.append("")
        lines.append(short)
    lines.append("")
    lines.append(f"承認 # {pid}".replace("# ","#"))
    lines.append(f"保留 # {pid}".replace("# ","#"))
    lines.append(f"却下 # {pid}".replace("# ","#"))
    return "\n".join(lines)

def run_once():
    c = conn()
    try:
        ensure_cols(c)
        rows = c.execute("""
            select
              id,title,description,source_ai,target_system,improvement_type,
              coalesce(status,'') as status,
              coalesce(project_decision,'') as project_decision,
              coalesce(dev_stage,'') as dev_stage,
              coalesce(notified_at,'') as notified_at,
              coalesce(priority,0) as priority
            from dev_proposals
            where coalesce(source_ai,'') in ('self_improve','cto','coo')
              and coalesce(notified_at,'')=''
              and coalesce(dev_stage,'') not in ('merged','closed')
              and coalesce(status,'') in ('new','pending','approved')
              and (
                    coalesce(priority,0) >= 40
                 or coalesce(source_ai,'') in ('self_improve','cto')
              )
            order by coalesce(priority,0) desc, id asc
            limit 10
        """).fetchall()
        done = 0
        for r in rows:
            msg = build_msg(r)
            tg(msg)
            c.execute("""
                update dev_proposals
                set notified_at=datetime('now'),
                    notified_msg_id='sent'
                where id=?
            """, (int(r["id"]),))
            try:
                c.execute("""
                    insert into ceo_hub_events(event_type,title,body,proposal_id,pr_url,created_at,sent_at)
                    values(?,?,?,?,?,datetime('now'),datetime('now'))
                """, ("proposal_for_ceo", r["title"], msg, int(r["id"]), "",))
            except Exception:
                pass
            done += 1
        c.commit()
        print(f"ceo_hub_sender_done={done}", flush=True)
    finally:
        c.close()

if __name__ == "__main__":
    while True:
        try:
            run_once()
        except Exception as e:
            print(f"ceo_hub_sender_error={e!r}", flush=True)
        time.sleep(15)
