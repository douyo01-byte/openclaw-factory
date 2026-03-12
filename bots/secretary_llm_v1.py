import json
import os
import sqlite3
import time
from pathlib import Path

import requests

DB = os.environ.get("DB_PATH", "/Users/doyopc/AI/openclaw-factory/data/openclaw.db")
BOT_TOKEN = (os.environ.get("TELEGRAM_CEO_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
OPENAI_API_KEY = (os.environ.get("OPENAI_API_KEY") or "").strip()
print(f"[secretary_boot] OPENAI_API_KEY_LEN={len(OPENAI_API_KEY)}", flush=True)
OPENAI_MODEL = (os.environ.get("OPENAI_MODEL") or "gpt-4o-mini").strip()

ROOT = Path(__file__).resolve().parent.parent
OBS = ROOT / "obs"
LOGS = ROOT / "logs"

def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}

def one(conn, sql, params=()):
    r = conn.execute(sql, params).fetchone()
    return r[0] if r else None

def fetch_dashboard_facts(conn):
    total = one(conn, "select count(*) from dev_proposals") or 0
    merged = one(conn, "select count(*) from dev_proposals where coalesce(status,'')='merged'") or 0
    approved = one(conn, "select count(*) from dev_proposals where coalesce(status,'')='approved'") or 0
    open_pr = one(conn, "select count(*) from dev_proposals where coalesce(pr_status,'')='open' or coalesce(status,'')='open'") or 0
    waiting = one(conn, "select count(*) from proposal_state where coalesce(stage,'')='waiting_answer'") or 0
    latest = conn.execute("""
        select id, coalesce(title,'')
        from dev_proposals
        order by id desc
        limit 1
    """).fetchone()
    latest_merged = conn.execute("""
        select id, coalesce(title,'')
        from dev_proposals
        where coalesce(status,'')='merged'
        order by id desc
        limit 1
    """).fetchone()
    top_backlog = conn.execute("""
        select id, coalesce(title,''), coalesce(project_decision,''), coalesce(guard_status,''), coalesce(priority,0)
        from dev_proposals
        where coalesce(status,'')='approved'
          and not (coalesce(project_decision,'')='execute_now' and coalesce(guard_status,'')='safe')
        order by coalesce(priority,0) asc, id desc
        limit 3
    """).fetchall()
    return {
        "total": total,
        "merged": merged,
        "approved": approved,
        "open_pr": open_pr,
        "waiting": waiting,
        "latest": {"id": latest[0], "title": latest[1]} if latest else None,
        "latest_merged": {"id": latest_merged[0], "title": latest_merged[1]} if latest_merged else None,
        "top_backlog": [
            {"id": r[0], "title": r[1], "decision": r[2], "guard": r[3], "priority": r[4]}
            for r in top_backlog
        ],
    }

def build_context(conn):
    health = load_json(OBS / "company_health_score.json")
    supply = load_json(OBS / "supply_adoption_metrics.json")
    integrity_lines = []
    try:
        p = LOGS / "db_integrity_check_v1.log"
        if p.exists():
            integrity_lines = p.read_text(encoding="utf-8").splitlines()[-5:]
    except Exception:
        integrity_lines = []
    ctx = {
        "company_health": health,
        "supply_adoption": supply,
        "db_integrity_recent": integrity_lines,
        "dashboard_facts": fetch_dashboard_facts(conn),
    }
    return json.dumps(ctx, ensure_ascii=False, indent=2)

def ask_llm(user_text, context_text):
    if not OPENAI_API_KEY:
        return (
            "今の状況です。\n"
            "・LLMキー未設定のため簡易応答です\n"
            "・詳細ダッシュボード生成は可能ですが、自然文要約は未接続です"
        )
    system = (
        "あなたは OpenClaw の秘書AIです。"
        "ユーザーの質問に対して、日本語で短く自然に返答してください。"
        "箇条書きは最大3点まで。"
        "事実は与えられた context のみを使うこと。"
        "わからないことは推測しない。"
        "『今どう？』『何が詰まってる？』『maturityは何%？』のような質問には、"
        "先に結論、その後に最大3項目で理由、最後に次の一手を1行で返す。"
    )
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": f"question:\n{user_text}\n\ncontext:\n{context_text}"},
        ],
        "temperature": 0.2,
    }
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"].strip()

def send(chat_id, text):
    if not BOT_TOKEN or not chat_id:
        return False, "missing_token_or_chat"
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": str(chat_id), "text": text},
        timeout=30,
    )
    r.raise_for_status()
    return True, ""

def ensure_cols(conn):
    cols = {r[1] for r in conn.execute("pragma table_info(inbox_commands)")}
    if "processed" not in cols:
        conn.execute("alter table inbox_commands add column processed integer default 0")
    if "applied_at" not in cols:
        conn.execute("alter table inbox_commands add column applied_at text")
    if "error" not in cols:
        conn.execute("alter table inbox_commands add column error text")
    if "status" not in cols:
        conn.execute("alter table inbox_commands add column status text default 'new'")
    if "chat_id" not in cols:
        conn.execute("alter table inbox_commands add column chat_id text")

def next_row(conn):
    return conn.execute("""
        select id, coalesce(chat_id,''), coalesce(text,'')
        from inbox_commands
        where coalesce(processed,0)=0
          and coalesce(status,'') not in ('company_done','company_error','secretary_done','secretary_error')
        order by id asc
        limit 1
    """).fetchone()

def mark(conn, rid, status, err=None):
    conn.execute(
        "update inbox_commands set processed=1,status=?,applied_at=datetime('now'),error=? where id=?",
        (status, err, rid),
    )
    conn.commit()

def run_once():
    conn = sqlite3.connect(DB, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("pragma busy_timeout=30000")
    ensure_cols(conn)
    row = next_row(conn)
    if not row:
        print("secretary_done=0", flush=True)
        conn.close()
        return
    rid = int(row[0])
    chat_id = str(row[1] or "").strip()
    text = str(row[2] or "").strip()
    try:
        context_text = build_context(conn)
        reply = ask_llm(text, context_text)
        ok, err = send(chat_id, reply)
        if ok:
            mark(conn, rid, "secretary_done", None)
            print("secretary_done=1", flush=True)
        else:
            mark(conn, rid, "secretary_error", err)
            print(f"secretary_error={err}", flush=True)
    except Exception as e:
        mark(conn, rid, "secretary_error", repr(e)[:500])
        print(f"secretary_error={e}", flush=True)
    finally:
        conn.close()

if __name__ == "__main__":
    while True:
        run_once()
        time.sleep(5)
