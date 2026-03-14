from __future__ import annotations
import os
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
STATE_PATH = Path("data/ai_meeting_digest_v1.state")

WINDOW_MIN = int(os.environ.get("AI_MEETING_DIGEST_WINDOW_MIN", "20"))
MIN_MERGED = int(os.environ.get("AI_MEETING_DIGEST_MIN_MERGED", "2"))
MIN_PR = int(os.environ.get("AI_MEETING_DIGEST_MIN_PR", "2"))
MIN_LEARN = int(os.environ.get("AI_MEETING_DIGEST_MIN_LEARN", "2"))
COOLDOWN_MIN = int(os.environ.get("AI_MEETING_DIGEST_COOLDOWN_MIN", "15"))

def connect():
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=30000")
    return con

def load_last_id() -> int:
    try:
        return int(STATE_PATH.read_text(encoding="utf-8").strip() or "0")
    except Exception:
        return 0

def save_last_id(v: int):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(str(v), encoding="utf-8")

def recent_ai_meeting_exists(con: sqlite3.Connection) -> bool:
    row = con.execute("""
        select 1
        from ceo_hub_events
        where coalesce(event_type,'')='ai_meeting'
          and created_at >= datetime('now', ?)
        order by id desc
        limit 1
    """, (f"-{COOLDOWN_MIN} minutes",)).fetchone()
    return bool(row)

def counts_since(con: sqlite3.Connection, last_id: int):
    row = con.execute("""
        select
          coalesce(max(id),0) as max_id,
          sum(case when coalesce(event_type,'')='merged' then 1 else 0 end) as merged_cnt,
          sum(case when coalesce(event_type,'')='pr_created' then 1 else 0 end) as pr_cnt,
          sum(case when coalesce(event_type,'')='learning_result' then 1 else 0 end) as learn_cnt,
          sum(case when coalesce(event_type,'')='ai_employee' then 1 else 0 end) as emp_cnt
        from ceo_hub_events
        where id > ?
          and created_at >= datetime('now', ?)
    """, (last_id, f"-{WINDOW_MIN} minutes")).fetchone()
    return {
        "max_id": int(row["max_id"] or 0),
        "merged": int(row["merged_cnt"] or 0),
        "pr": int(row["pr_cnt"] or 0),
        "learn": int(row["learn_cnt"] or 0),
        "emp": int(row["emp_cnt"] or 0),
    }

def top_learning_titles(con: sqlite3.Connection, last_id: int, limit: int = 3):
    rows = con.execute("""
        select title
        from ceo_hub_events
        where id > ?
          and coalesce(event_type,'')='learning_result'
          and created_at >= datetime('now', ?)
        order by id desc
        limit ?
    """, (last_id, f"-{WINDOW_MIN} minutes", limit)).fetchall()
    out = []
    for r in rows:
        t = (r["title"] or "").strip()
        if t.startswith("学 習 反 映 :"):
            t = t.replace("学 習 反 映 :", "", 1).strip()
        out.append(t[:120])
    return list(reversed(out))

def top_merged_titles(con: sqlite3.Connection, last_id: int, limit: int = 2):
    rows = con.execute("""
        select title
        from ceo_hub_events
        where id > ?
          and coalesce(event_type,'')='merged'
          and created_at >= datetime('now', ?)
        order by id desc
        limit ?
    """, (last_id, f"-{WINDOW_MIN} minutes", limit)).fetchall()
    out = []
    for r in rows:
        t = (r["title"] or "").strip()
        if t.startswith("統 合 完 了 :"):
            t = t.replace("統 合 完 了 :", "", 1).strip()
        out.append(t[:120])
    return list(reversed(out))

def should_emit(c: dict) -> bool:
    return (
        c["merged"] >= MIN_MERGED
        or c["pr"] >= MIN_PR
        or c["learn"] >= MIN_LEARN
        or (c["merged"] + c["pr"] + c["learn"] + c["emp"]) >= 6
    )

def build_title(c: dict) -> str:
    return f"OpenClaw 定例会議 merged={c['merged']} pr={c['pr']} learn={c['learn']} emp={c['emp']}"

def build_body(c: dict, merged_titles: list[str], learn_titles: list[str]) -> str:
    lines = [
        "OpenClaw 会議メモ",
        f"集計窓: 直近{WINDOW_MIN}分",
        f"統合: {c['merged']}件 / PR作成: {c['pr']}件 / 学習反映: {c['learn']}件 / AI社員: {c['emp']}件",
    ]
    if merged_titles:
        lines.append("")
        lines.append("主な統合")
        for x in merged_titles:
            lines.append(f"- {x}")
    if learn_titles:
        lines.append("")
        lines.append("主な学習反映")
        for x in learn_titles:
            lines.append(f"- {x}")
    lines.append("")
    lines.append("次のアクション")
    if c["pr"] > c["merged"]:
        lines.append("- PR消化を優先")
    else:
        lines.append("- 供給継続で次の改善を回す")
    if c["learn"] >= 3:
        lines.append("- 学習反映の高頻度帯を監視")
    else:
        lines.append("- 会議材料が増えるまで継続観測")
    return "\n".join(lines)

def insert_ai_meeting(con: sqlite3.Connection, title: str, body: str):
    con.execute("""
        insert into ceo_hub_events(event_type,title,body,created_at)
        values('ai_meeting', ?, ?, datetime('now'))
    """, (title, body))
    con.commit()

def main():
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    last_id = load_last_id()
    con = connect()
    try:
        c = counts_since(con, last_id)
        if c["max_id"] <= last_id:
            print("skip=no_new_events")
            return
        if recent_ai_meeting_exists(con):
            save_last_id(c["max_id"])
            print("skip=recent_ai_meeting")
            return
        if not should_emit(c):
            save_last_id(c["max_id"])
            print(f"skip=below_threshold merged={c['merged']} pr={c['pr']} learn={c['learn']} emp={c['emp']}")
            return
        merged_titles = top_merged_titles(con, last_id, 2)
        learn_titles = top_learning_titles(con, last_id, 3)
        title = build_title(c)
        body = build_body(c, merged_titles, learn_titles)
        insert_ai_meeting(con, title, body)
        save_last_id(c["max_id"])
        print(f"inserted {title}")
    finally:
        con.close()

if __name__ == "__main__":
    main()
