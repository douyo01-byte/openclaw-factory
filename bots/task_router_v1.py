from __future__ import annotations
import os, time, sqlite3

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = float(os.environ.get("TASK_ROUTER_SLEEP", "5"))

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
      mode text not null default 'FAST',
      target_bot text not null default 'kaikun02',
      task_text text not null,
      status text not null default 'new',
      created_at text default (datetime('now')),
      updated_at text default (datetime('now'))
    )
    """)
    c.execute("create index if not exists idx_router_tasks_status on router_tasks(status, target_bot, mode)")
    cols = {r["name"] for r in c.execute("pragma table_info(inbox_commands)").fetchall()}
    if "router_status" not in cols:
        c.execute("alter table inbox_commands add column router_status text default ''")
    if "router_target" not in cols:
        c.execute("alter table inbox_commands add column router_target text default ''")
    if "router_mode" not in cols:
        c.execute("alter table inbox_commands add column router_mode text default ''")

def classify(text: str):
    t = (text or "").lower()

    if "[doc]" in t:
        return "DOC", "kaikun02"
    if "[think]" in t or "[deep]" in t:
        return "THINK", "kaikun04"
    if "[fast]" in t:
        return "FAST", "kaikun02"

    if any(x in t for x in ["schema", "pipeline", "db", "設計", "構造", "統合"]):
        return "THINK", "kaikun04"
    if any(x in t for x in ["分類", "classify", "棚卸し", "一覧", "どれ"]):
        return "FAST", "kaikun02"
    if any(x in t for x in ["docs", "handover", "readme", "文章", "文面"]):
        return "DOC", "kaikun02"

    return "FAST", "kaikun02"

def shorten(text: str):
    lines = (text or "").splitlines()
    if len(lines) > 12:
        lines = lines[:12]
    return "\n".join(lines).strip()

def tick():
    c = conn()
    try:
        ensure_schema(c)
        rows = c.execute("""
        select id, coalesce(text,'') as text
        from inbox_commands
        where coalesce(router_status,'')=''
          and coalesce(text,'')<>''
        order by id asc
        limit 20
        """).fetchall()

        done = 0
        for r in rows:
            mode, target = classify(r["text"])
            task_text = f"[{mode}]\n{shorten(r['text'])}"
            c.execute("""
            insert into router_tasks(source_command_id, mode, target_bot, task_text, status, created_at, updated_at)
            values(?,?,?,?, 'new', datetime('now'), datetime('now'))
            """, (r["id"], mode, target, task_text))
            c.execute("""
            update inbox_commands
            set router_status='routed',
                router_target=?,
                router_mode=?,
                updated_at=datetime('now')
            where id=?
            """, (target, mode, r["id"]))
            done += 1

        if done:
            c.commit()
        print(f"[task_router_v1] routed={done}", flush=True)
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
