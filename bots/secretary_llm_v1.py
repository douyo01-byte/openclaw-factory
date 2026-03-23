import json
import os
import sqlite3
import time
from pathlib import Path

import requests

DB = (
    os.environ.get("OCLAW_DB_PATH")
    or os.environ.get("FACTORY_DB_PATH")
    or os.environ.get("DB_PATH")
    or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
)
BOT_TOKEN = (
    os.environ.get("TELEGRAM_CEO_BOT_TOKEN")
    or os.environ.get("TELEGRAM_BOT_TOKEN")
    or ""
).strip()
DEFAULT_CHAT_ID = (
    os.environ.get("TELEGRAM_CHAT_ID")
    or os.environ.get("TELEGRAM_CEO_CHAT_ID")
    or ""
).strip()
OPENAI_API_KEY = (os.environ.get("OPENAI_API_KEY") or "").strip()
OPENAI_MODEL = (os.environ.get("OPENAI_MODEL") or "gpt-4o-mini").strip()

ROOT = Path(__file__).resolve().parent.parent
OBS = ROOT / "obs"
LOGS = ROOT / "logs"

ENTRY_GATE_PATH = ROOT / "prompts" / "kaikun04_entry_gate.txt"
STARTER_PATH = Path("/Users/doyopc/AI/openclaw-factory-docs/docs/04_KAIKUN04_STARTER.md")

print(f"[secretary_boot] OPENAI_API_KEY_LEN={len(OPENAI_API_KEY)}", flush=True)


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def one(conn, sql, params=()):
    r = conn.execute(sql, params).fetchone()
    return r[0] if r else None


def load_entry_gate():
    try:
        return ENTRY_GATE_PATH.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def load_starter():
    try:
        return STARTER_PATH.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def build_system_prompt():
    base = "あなたは OpenClaw 専属の COO / 右腕です。日本語で自然に、断定しすぎず、OpenClaw の内部事情を知る実務家として答えてください。事実は context のみを使うこと。推測は禁止。質問が経営・弱点・次の一手なら、1) 結論 2) 根拠 3) 次の一手 の順で簡潔に返す。必要なら作業チャットに貼れる短い指示も出す。箇条書きは多くても 4 個まで。"
    parts = [x for x in [load_entry_gate(), load_starter(), base] if x]
    return "\n\n".join(parts)


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
            {
                "id": r[0],
                "title": r[1],
                "decision": r[2],
                "guard": r[3],
                "priority": r[4],
            }
            for r in top_backlog
        ],
    }




def load_role_registry():
    try:
        return Path("/Users/doyopc/AI/openclaw-factory-docs/docs/02_ROLE_REGISTRY.md").read_text(encoding="utf-8")
    except:
        return ""

def build_context(conn):
    health = load_json(OBS / "company_health_score.json")
    supply = load_json(OBS / "supply_adoption_metrics.json")
    integrity_lines = []
    runtime_classification = ""

    try:
        p = LOGS / "db_integrity_check_v1.log"
        if p.exists():
            integrity_lines = p.read_text(encoding="utf-8").splitlines()[-5:]
    except Exception:
        integrity_lines = []

    try:
        rc = ROOT / "reports" / "audit_20260316" / "runtime_classification_20260316.md"
        if rc.exists():
            runtime_classification = rc.read_text(encoding="utf-8")
    except Exception:
        runtime_classification = ""

    
    roles = load_role_registry()
    ctx = {
        "roles": roles,

        "company_health": health,
        "supply_adoption": supply,
        "db_integrity_recent": integrity_lines,
        "dashboard_facts": fetch_dashboard_facts(conn),
        "runtime_classification": runtime_classification,
    }
    return json.dumps(ctx, ensure_ascii=False, indent=2)




def enforce_governance(user_text):
    t = (user_text or "").lower()

    banned = ["新bot", "新規bot", "watcher追加", "selector", "bridge", "normalizer"]
    for b in banned:
        if b in t:
            return "reject", f"却下: {b} は禁止ルール"

    return "ok", ""


def detect_duplicate(text):
    keywords = ["selector", "bridge", "normalizer"]
    raw = normalize_gate_text(text).lower()
    for k in keywords:
        if k in raw:
            return True
    return False

def normalize_gate_text(text):
    return " ".join((text or "").replace("\u3000", " ").split())

def looks_like_code_or_log(text):
    raw = text or ""
    if len(raw) >= 400:
        return True
    markers = [
        "cd ~/AI/",
        "git ",
        "launchctl ",
        "sqlite3 ",
        "python3 - <<'PY'",
        "Traceback (most recent call last):",
        'File "',
        "select ",
        "from ",
        "where ",
        "cat > ",
        "#!/bin/zsh",
    ]
    hit = sum(1 for m in markers if m in raw)
    if hit >= 2:
        return True
    if raw.count("\n") >= 8:
        return True
    return False

def should_use_think(text):
    raw = normalize_gate_text(text)
    t = raw.lower()
    analysis_words = ["比較", "分析", "設計", "構造", "統合", "方針", "根拠", "整理"]
    if "[think]" in t or "[deep]" in t:
        return len(raw) >= 40
    if len(raw) < 120:
        return False
    return any(k in raw for k in analysis_words)

def classify_input(text):
    raw = normalize_gate_text(text)
    if looks_like_code_or_log(text):
        return "code_or_log"
    if any(k in raw for k in ["進捗", "状態", "status", "health", "要約", "まとめ"]):
        return "status"
    if any(k in raw for k in ["改善", "強化"]):
        return "improvement"
    if any(k in raw for k in ["追加", "作りたい"]):
        return "feature"
    if "緊急" in raw:
        return "urgent"
    return "other"

def build_governed_prompt(user_text, context_text):
    input_type = classify_input(user_text)
    extra = ""
    if input_type == "code_or_log":
        extra = """

【 Code/Log Handling】
- コードやログの貼り付けは全文解説しない
- まず 1) 何が起きたか 2) 問題箇所 3) 次の一手 を短く返す
- 新しい bot / watcher / bridge を安易に提案しない
"""
    rule = """
【 Execution Rule】
1. SINGLE SOURCE確認
2. ROLE確認
3. 重複チェック
4. 統合先決定
5. 新規禁止
【 Absolute Rules】
- 新規bot禁止
- watcher増殖禁止
- bridge追加禁止
- normalizer追加禁止
- 重複機能禁止
- 既存優先統合
""" + extra
    return f"{rule}\n\ninput_type:\n{input_type}\n\ninput:\n{user_text}\n\ncontext:\n{context_text}"

def ask_llm(user_text, context_text):

    use_think = should_use_think(user_text)

    if not OPENAI_API_KEY:
        return "OpenClaw COOです。\n今は簡易モードです。\n事実ベースで短く答えます。"

    
    
    if detect_duplicate(user_text):
        return "却下: 重複機能の可能性"

    mode, reason = enforce_governance(user_text)

    if mode == "reject":
        return reason

    mode_hint = "THINK" if use_think else "FAST"
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": f"[ENTRY_MODE:{mode_hint}]\n" + build_governed_prompt(user_text, context_text)},
        ],
    }
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=90 if use_think else 45,
    )
    if not r.ok:
        body = ""
        try:
            body = r.text[:2000]
        except Exception:
            body = "<no_body>"
        print(f"[secretary_openai_error] status={r.status_code} body={body}", flush=True)
        return f"OpenAI_ERROR {r.status_code}: {body[:500]}"
    data = r.json()
    return data["choices"][0]["message"]["content"].strip()



def send(chat_id, text):
    chat_id = str(chat_id or "").strip() or DEFAULT_CHAT_ID
    if not BOT_TOKEN or not chat_id:
        print(f"[secretary_send] missing token/chat bot_len={len(BOT_TOKEN)} chat_id={chat_id}", flush=True)
        return False, "missing_token_or_chat"
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": str(chat_id), "text": text},
            timeout=30,
        )
        r.raise_for_status()
        print(f"[secretary_send] ok chat_id={chat_id} text_head={repr((text or '')[:60])}", flush=True)
        return True, ""
    except Exception as e:
        print(f"[secretary_send] error chat_id={chat_id} err={repr(e)}", flush=True)
        return False, repr(e)[:500]


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
          and coalesce(router_target,'')='secretary'
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


def normalize_user_text(text):
    return " ".join((text or "").strip().split())


def is_terminal_dump(text):
    t = (text or "").strip()
    return (
        t.startswith("Last login:")
        or "doyopc@DoyonoMac-mini" in t
        or t.startswith("%")
        or t.startswith("(.venv)")
    )


def route_special(text):
    t = (text or "").strip()
    if t == "/help":
        return "help_done", "このコマンドは別worker担当です。"
    if t == "/company":
        return "company_done", "このコマンドは別worker担当です。"
    if t.startswith("/meeting"):
        return "meeting_done", "このコマンドは別worker担当です。"
    return None, None


def run_once():
    conn = sqlite3.connect(DB, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass

    ensure_cols(conn)

    while True:
        r = next_row(conn)
        if not r:
            break

        rid = int(r[0])
        chat_id = str(r[1] or "").strip()
        text = normalize_user_text(r[2])

        try:
            special_status, special_reply = route_special(text)
            if special_status:
                if special_reply:
                    send(chat_id, special_reply)
                mark(conn, rid, special_status, None)
                continue

            if is_terminal_dump(text):
                mark(conn, rid, "secretary_error", "terminal_dump_like_input")
                continue

            ctx = build_context(conn)
            out = ask_llm(text, ctx)
            ok, err = send(chat_id, out)
            if ok:
                mark(conn, rid, "secretary_done", None)
            else:
                mark(conn, rid, "secretary_error", err)
        except Exception as e:
            mark(conn, rid, "secretary_error", repr(e)[:500])

    conn.close()


if __name__ == "__main__":
    while True:
        run_once()
        time.sleep(5)
