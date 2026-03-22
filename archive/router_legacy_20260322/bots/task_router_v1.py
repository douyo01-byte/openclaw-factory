from __future__ import annotations
import os
import time
import sqlite3
import re

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = float(os.environ.get("TASK_ROUTER_SLEEP", "5"))
THINK_MIN_LEN = int(os.environ.get("TASK_ROUTER_THINK_MIN_LEN", "120"))
DEDUP_MINUTES = int(os.environ.get("TASK_ROUTER_DEDUP_MINUTES", "15"))
FAST_TIMEOUT = int(os.environ.get("TASK_ROUTER_FAST_TIMEOUT", "180"))
THINK_TIMEOUT = int(os.environ.get("TASK_ROUTER_THINK_TIMEOUT", "900"))

STATUS_PATTERNS = [
    "進 捗 ", "状 況 ", "状 態 ", "health", "ヘ ル ス ", "watcher", "監 視 ", "open_pr"
]
HEALTH_PATTERNS = [
    "runtime", "ラ ン キ ン グ ", "弱 点 ", "次 の 作 業 候 補 ", "ボ ト ル ネ ッ ク "
]
THINK_PATTERNS = [
    "[think]", "[deep]", "比 較 ", "分 析 ", "長 文 ", "整 理 し て ", "設 計 ", "構 造 ",
    "統 合 ", "統 合 案 ", "ア ー キ テ ク チ ャ ", "方 針 ", "根 拠 ", "private reply", "router", "docs"
]
FAST_PATTERNS = [
    "[fast]", "教 え て ", "一 覧 ", "ど れ ", "何 件 "
]

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    try:
        c.execute("pragma journal_mode=WAL")
    except Exception:
        pass
    return c

def ensure_schema(c):
    c.execute("""
    create table if not exists router_tasks(
      id integer primary key autoincrement,
      source_command_id integer,
      source_chat_id text default '',
      mode text not null default 'FAST',
      target_bot text not null default 'kaikun02',
      task_text text not null,
      task_hash text default '',
      intent text default '',
      status text not null default 'new',
      parent_task_id integer,
      created_at text default (datetime('now')),
      updated_at text default (datetime('now')),
      started_at text default '',
      finished_at text default '',
      result_text text default '',
      timeout_sec integer not null default 300,
      reply_text text default '',
      sent_message_id text default ''
    )
    """)
    rt_cols = {r["name"] for r in c.execute("pragma table_info(router_tasks)").fetchall()}
    for sql, name in [
        ("alter table router_tasks add column source_chat_id text default ''", "source_chat_id"),
        ("alter table router_tasks add column task_hash text default ''", "task_hash"),
        ("alter table router_tasks add column intent text default ''", "intent"),
        ("alter table router_tasks add column parent_task_id integer", "parent_task_id"),
    ]:
        if name not in rt_cols:
            c.execute(sql)
    c.execute("create index if not exists idx_router_tasks_status on router_tasks(status, target_bot, mode)")
    c.execute("create index if not exists idx_router_tasks_hash on router_tasks(source_chat_id, intent, task_hash, status)")

    cols = {r["name"] for r in c.execute("pragma table_info(inbox_commands)").fetchall()}
    if "router_status" not in cols:
        c.execute("alter table inbox_commands add column router_status text default ''")
    if "router_target" not in cols:
        c.execute("alter table inbox_commands add column router_target text default ''")
    if "router_mode" not in cols:
        c.execute("alter table inbox_commands add column router_mode text default ''")
    if "router_task_id" not in cols:
        c.execute("alter table inbox_commands add column router_task_id integer")
    if "chat_id" not in cols:
        c.execute("alter table inbox_commands add column chat_id text")

def normalize(text: str):
    return " ".join((text or "").strip().split())

def shorten(text: str):
    lines = (text or "").splitlines()
    if len(lines) > 12:
        lines = lines[:12]
    return "\n".join(lines).strip()

def task_hash(text: str):
    t = normalize(text).lower()
    t = re.sub(r"\[task_id:\d+\]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:300]

def detect_intent(text: str):
    t = normalize(text).lower()
    if any(x in t for x in ["比 較 ", "分 析 ", "設 計 ", "構 造 ", "統 合 ", "方 針 ", "根 拠 ", "長 文 "]):
        return "analysis"
    if any(x in t for x in ["docs", "readme", "handover", "md", "文 書 "]):
        return "docs"
    if any(x in t for x in STATUS_PATTERNS):
        return "status"
    if any(x in t for x in HEALTH_PATTERNS):
        return "health"
    return "general"

def classify(text: str):
    raw = text or ""
    t = normalize(raw).lower()
    norm = normalize(raw)
    intent = detect_intent(raw)
    is_short = len(norm) < THINK_MIN_LEN
    explicit_think = any(x in t for x in THINK_PATTERNS)
    explicit_fast = any(x in t for x in FAST_PATTERNS)

    if explicit_think and not is_short:
        return "THINK", "kaikun04", intent, THINK_TIMEOUT
    if not is_short and intent in ("analysis", "docs"):
        return "THINK", "kaikun04", intent, THINK_TIMEOUT
    if intent in ("status", "health"):
        return "FAST", "kaikun02", intent, FAST_TIMEOUT
    if explicit_fast:
        return "FAST", "kaikun02", intent, FAST_TIMEOUT
    return "FAST", "kaikun02", intent, FAST_TIMEOUT

def find_active_duplicate(c, chat_id: str, intent: str, h: str):
    return c.execute("""
    select id, status
    from router_tasks
    where coalesce(source_chat_id,'')=?
      and coalesce(intent,'')=?
      and coalesce(task_hash,'')=?
      and coalesce(status,'') in ('new','started')
      and datetime(created_at) >= datetime('now', ?)
    order by id desc
    limit 1
    """, (chat_id, intent, h, f"-{DEDUP_MINUTES} minutes")).fetchone()

def tick():
    c = conn()
    try:
        ensure_schema(c)
        rows = c.execute("""
        select id, coalesce(chat_id,'') as chat_id, coalesce(text,'') as text
        from inbox_commands
        where coalesce(router_status,'')=''
          and coalesce(text,'')<>''
          and coalesce(source,'') not in ('private_reply_bridge','tg_private_chat_log','manual_test')
        order by id asc
        limit 20
        """).fetchall()
        done = 0
        for r in rows:
            raw = r["text"]
            mode, target, intent, timeout_sec = classify(raw)
            h = task_hash(raw)
            dup = find_active_duplicate(c, str(r["chat_id"] or ""), intent, h)
            if dup:
                c.execute("""
                update inbox_commands
                set router_status='dedup_reused',
                    router_target=?,
                    router_mode=?,
                    router_task_id=?,
                    updated_at=datetime('now')
                where id=?
                """, (target, mode, dup["id"], r["id"]))
                done += 1
                continue
            task_text = f"[{mode}]\n{shorten(raw)}"
            c.execute("""
            insert into router_tasks(
              source_command_id, source_chat_id, mode, target_bot, task_text,
              task_hash, intent, status, timeout_sec, created_at, updated_at
            )
            values(?,?,?,?,?,?,?,?,?,datetime('now'),datetime('now'))
            """, (r["id"], str(r["chat_id"] or ""), mode, target, task_text, h, intent, "new", timeout_sec))
            task_id = c.execute("select last_insert_rowid()").fetchone()[0]
            c.execute("""
            update inbox_commands
            set router_status='routed',
                router_target=?,
                router_mode=?,
                router_task_id=?,
                updated_at=datetime('now')
            where id=?
            """, (target, mode, task_id, r["id"]))
            done += 1
        if done:
            c.commit()
        print(f"[task_router_v1] done={done}", flush=True)
    finally:
        c.close()

def main():
    while True:
        try:
            tick()
        except Exception as e:
            print(f"[task_router_v1] err={e!r}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
