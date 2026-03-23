import os
import re
import sqlite3
import time
from pathlib import Path

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or "data/openclaw.db"

URL_ONLY_RE = re.compile(r"^\s*https?://\S+\s*$", re.I)
THINK_HINTS = ["比較", "分析", "設計", "構造", "統合", "方針", "根拠", "整理"]
STATUS_HINTS = ["進捗", "状態", "status", "health", "要約", "まとめ"]

def normalize_text(text):
    return " ".join((text or "").replace("\u3000", " ").split())

def conn():
    db = Path(DB).expanduser().resolve()
    db.parent.mkdir(parents=True, exist_ok=True)
    print(f"[private_reply_to_inbox_v1][db_open] path={db} exists={db.exists()} parent_exists={db.parent.exists()}", flush=True)
    c = sqlite3.connect(str(db), timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA busy_timeout=30000")
    try:
        c.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass
    return c

def ensure():
    with conn() as c:
        c.execute("CREATE INDEX IF NOT EXISTS idx_tg_private_chat_log_ingested ON tg_private_chat_log(router_ingested, id)")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_inbox_commands_chat_msg ON inbox_commands(chat_id, message_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_inbox_commands_private_recent ON inbox_commands(source, chat_id, created_at)")
        c.commit()

def is_noise(text):
    t = normalize_text(text)
    if not t:
        return True
    if len(t) <= 1:
        return True
    if URL_ONLY_RE.match(t):
        return True
    return False

def classify_mode(text):
    raw = normalize_text(text)
    low = raw.lower()
    if "[think]" in low or "[deep]" in low:
        return "think"
    if len(raw) <= 40 and any(k in raw for k in STATUS_HINTS):
        return "fast"
    if len(raw) >= 180 and any(k in raw for k in THINK_HINTS):
        return "think"
    return "fast"

def recent_duplicate(c, chat_id, text):
    t = normalize_text(text)
    row = c.execute(
        """
        select id
        from inbox_commands
        where coalesce(source,'')='tg_private_chat_log'
          and coalesce(chat_id,'')=?
          and trim(replace(replace(coalesce(text,''), char(10), ' '), char(13), ' '))=?
          and created_at >= datetime('now','-20 seconds')
        order by id desc
        limit 1
        """,
        (str(chat_id), t),
    ).fetchone()
    return row is not None

def mark_ingested(c, row_id, status):
    c.execute(
        """
        update tg_private_chat_log
        set router_ingested=?, router_ingested_at=datetime('now')
        where id=?
        """,
        (status, int(row_id)),
    )

def run_once():
    done = 0
    with conn() as c:
        rows = c.execute(
            """
            select id, coalesce(update_id,0) as update_id, coalesce(message_id,0) as message_id,
                   coalesce(chat_id,0) as chat_id, coalesce(text,'') as text, coalesce(created_at,'') as created_at
            from tg_private_chat_log
            where coalesce(router_ingested,'')=''
            order by id asc
            limit 50
            """
        ).fetchall()
        for r in rows:
            try:
                raw_text = r["text"] or ""
                text = normalize_text(raw_text)
                if is_noise(text):
                    mark_ingested(c, r["id"], "skipped_noise")
                    c.commit()
                    done += 1
                    continue
                if recent_duplicate(c, r["chat_id"], text):
                    mark_ingested(c, r["id"], "skipped_dup")
                    c.commit()
                    done += 1
                    continue
                mode = classify_mode(text)
                c.execute(
                    """
                    insert or ignore into inbox_commands(
                        source, text, status, created_at, updated_at,
                        chat_id, message_id, received_at, update_id, processed,
                        router_status, router_target, router_mode, router_finish_status
                    ) values(
                        ?, ?, 'pending', datetime('now'), datetime('now'),
                        ?, ?, ?, ?, 0,
                        '', 'secretary', ?, ''
                    )
                    """,
                    (
                        "tg_private_chat_log",
                        text,
                        str(r["chat_id"]),
                        int(r["message_id"]),
                        r["created_at"] or "",
                        int(r["update_id"]),
                        mode,
                    ),
                )
                mark_ingested(c, r["id"], "yes")
                c.commit()
                done += 1
            except Exception as e:
                c.rollback()
                print(f"[private_reply_to_inbox_v1][row_error] id={r['id']} message_id={r['message_id']} err={e!r}", flush=True)
    print(f"[private_reply_to_inbox_v1] done={done}", flush=True)

if __name__ == "__main__":
    while True:
        try:
            ensure()
            run_once()
        except Exception as e:
            print(f"[private_reply_to_inbox_v1][error] {repr(e)}", flush=True)
        time.sleep(5)
