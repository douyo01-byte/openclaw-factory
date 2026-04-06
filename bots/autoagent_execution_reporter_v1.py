import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bots.autoagent_text_utils_v1 import clean_text, strip_task_header

DB = "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def ensure():
    with conn() as c:
        c.execute("""
        create table if not exists autoagent_execution_report_log (
          id integer primary key autoincrement,
          execution_log_id integer not null,
          report_type text not null default '',
          created_at text default (datetime('now')),
          unique(execution_log_id, report_type)
        )
        """)
        c.commit()

def compact_result(text: str) -> str:
    t = strip_task_header(text or "")
    lines = [x.strip() for x in t.split("\n") if x.strip()]

    kept = []
    for line in lines:
        if line.startswith("- "):
            kept.append(line)
        elif line.startswith("[EXEC]"):
            kept.append(line)
        elif line.startswith("script="):
            kept.append(line)
        elif not kept:
            kept.append(line)

    return clean_text("\n".join(kept[:12]))

def run_once():
    ensure()
    done = 0
    with conn() as c:
        rows = c.execute("""
        select
          l.id as log_id,
          l.action_text,
          t.reply_text
        from autoagent_execution_log l
        join router_tasks t on t.id = l.router_task_id
        where l.status='done'
        order by l.id desc
        limit 50
        """).fetchall()

        for r in rows:
            body = "\n".join([
                "【 AUTOAGENT EXECUTION 】",
                f"action: {clean_text(r['action_text'])}",
                "",
                "【 result 】",
                compact_result(r["reply_text"] or ""),
            ]).strip()

            source_key = f"autoagent_execution:{r['log_id']}"

            c.execute("""
            insert or ignore into ceo_hub_events(source, source_key, title, body, level, created_at)
            values(?,?,?,?,?,datetime('now'))
            """, (
                "autoagent_execution_reporter_v1",
                source_key,
                "AUTOAGENT EXECUTION",
                body,
                "info",
            ))

            c.execute("""
            update ceo_hub_events
            set body=?, title='AUTOAGENT EXECUTION', level='info'
            where source='autoagent_execution_reporter_v1'
              and source_key=?
            """, (body, source_key))

            c.execute("""
            insert or ignore into autoagent_execution_report_log(execution_log_id, report_type)
            values(?, 'ceo_hub')
            """, (r["log_id"],))

            done += 1

        c.commit()

    print(f"autoagent_execution_reporter_done={done}", flush=True)

if __name__ == "__main__":
    run_once()
