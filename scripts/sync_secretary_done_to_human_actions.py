import os
import re
import sqlite3

DB_PATH = os.environ.get("OCLAW_DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def extract_proposal_id(text):
    raw = text or ""
    patterns = [
        r"proposal_id\s*[:=]\s*(\d+)",
        r"#(\d+)",
        r"提\s*案\s*#?(\d+)",
    ]
    for pat in patterns:
        m = re.search(pat, raw, re.I)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass
    return None

def build_todo_from_text(text):
    raw = text or ""
    if "[TODO]" in raw:
        m = re.search(r"(\[TODO\][\s\S]*)", raw)
        return m.group(1).strip() if m else raw.strip()
    if "[HUMAN REQUIRED]" not in raw:
        return ""
    return (
        "[TODO]\n"
        "- 高 : Gmail作成 / 送信下書き確認\n"
        "- 高 : 送信先10件確認\n"
        "- 高 : 契約条件確認\n"
        "- 中 : NG表現確認\n"
        "- 中 : LP公開 / 導線確認\n"
        "- 中 : Instagram開設 or 運用先確認\n"
    )

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

conn.execute("""
create table if not exists human_actions (
  id integer primary key autoincrement,
  proposal_id integer,
  action_type text,
  action_detail text,
  result text,
  created_at datetime default current_timestamp
)
""")

rows = conn.execute("""
select
  id,
  proposal_id,
  coalesce(text,'') as text,
  coalesce(result,'') as result,
  coalesce(created_at,'') as created_at
from inbox_commands
where coalesce(status,'')='secretary_done'
order by id asc
limit 200
""").fetchall()

synced = 0

for r in rows:
    merged_text = (r["text"] or "") + "\n" + (r["result"] or "")
    todo = build_todo_from_text(merged_text)
    if not todo:
        continue

    proposal_id = r["proposal_id"]
    if proposal_id in (None, "", 0, "0"):
        proposal_id = extract_proposal_id(merged_text)
    if proposal_id in (None, "", 0, "0"):
        continue

    exists = conn.execute("""
    select id
    from human_actions
    where proposal_id=?
      and action_type='todo_generated'
      and action_detail=?
    limit 1
    """, (int(proposal_id), todo)).fetchone()

    if exists:
        continue

    conn.execute("""
    insert into human_actions(proposal_id, action_type, action_detail, result, created_at)
    values(?,?,?,?,datetime('now'))
    """, (
        int(proposal_id),
        "todo_generated",
        todo,
        "secretary_done",
    ))
    synced += 1

conn.commit()
print(f"synced {synced} secretary_done rows")
