from __future__ import annotations
import os, time, sqlite3, re

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = float(os.environ.get("TASK_ROUTER_SLEEP", "5"))
EXEC_ONLY_RE = re.compile(r"(?is)^\s*\[exec\]\s*\n\s*script\s*=\s*[A-Za-z0-9_.-]+\s*$")

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
    router_cols = {r["name"] for r in c.execute("pragma table_info(router_tasks)").fetchall()}
    router_required = {
        "source_command_id", "mode", "target_bot", "task_text", "status",
        "created_at", "updated_at",
    }
    router_missing = sorted(router_required - router_cols)
    if router_missing:
        raise RuntimeError(
            f"schema_missing table=router_tasks cols={','.join(router_missing)} "
            "apply migrations/20260513_router_core_schema_v1.sql first"
        )
    cols = {r["name"] for r in c.execute("pragma table_info(inbox_commands)").fetchall()}
    required = {"source", "text", "router_status", "router_target", "router_mode", "updated_at"}
    missing = sorted(required - cols)
    if missing:
        raise RuntimeError(
            f"schema_missing table=inbox_commands cols={','.join(missing)} "
            "apply migrations/20260513_router_core_schema_v1.sql first"
        )

def classify(text: str):
    raw = (text or "").strip()
    t = raw.lower()
    if EXEC_ONLY_RE.fullmatch(raw):
        return "EXEC", "ops_exec"
    if "[doc]" in t:
        return "DOC", "kaikun04"
    if "[think]" in t or "[deep]" in t:
        return "THINK", "kaikun04"
    if "[fast]" in t:
        return "FAST", "kaikun04"
    if any(x in t for x in ["schema", "pipeline", "db", "設 計 ", "構 造 ", "統合 "]):
        return "THINK", "kaikun04"
    if any(x in t for x in ["分 類 ", "classify", "棚 卸 し ", "一 覧 ", "ど れ "]):
        return "FAST", "kaikun04"
    if any(x in t for x in ["docs", "handover", "readme", "文 章 ", "文 面 "]):
        return "DOC", "kaikun04"
    return "FAST", "kaikun04"

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
        select id, coalesce(source,'') as source, coalesce(text,'') as text
        from inbox_commands
        where coalesce(router_status,'')=''
          and coalesce(text,'')<>''
        order by id asc
        limit 20
        """).fetchall()

        done = 0
        for r in rows:
            mode, target = '', 'kaikun04'
            body = shorten(r['text'])
            task_text = body if not mode else f"[{mode}]\n{body}"
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
