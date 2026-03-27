from __future__ import annotations
import json
import os
import sqlite3
import time
from pathlib import Path

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
ROOT = Path("/Users/doyopc/AI/openclaw-factory-daemon")
OUT = ROOT / "obs" / "self_improvement_feedback.json"
SLEEP = float(os.environ.get("SELF_IMPROVEMENT_FEEDBACK_METRICS_SLEEP", "30"))

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    try:
        c.execute("pragma journal_mode=WAL")
    except Exception:
        pass
    return c

def q1(c, sql: str, args=()):
    row = c.execute(sql, args).fetchone()
    if row is None:
        return 0
    v = list(row)[0]
    return 0 if v is None else v

def qrows(c, sql: str, args=()):
    return [dict(r) for r in c.execute(sql, args).fetchall()]

def collect():
    with conn() as c:
        summary = {
            "generated_at": qrows(c, "select datetime('now') as ts")[0]["ts"],
            "self_improvement_log_total": q1(c, "select count(*) from self_improvement_log"),
            "done_rows": q1(c, "select count(*) from self_improvement_log where coalesce(status,'')='done'"),
            "skipped_rows": q1(c, "select count(*) from self_improvement_log where coalesce(status,'')='skipped'"),
            "learning_done_rows": q1(c, "select count(*) from self_improvement_log where coalesce(learning_bridge_status,'')='done'"),
            "pattern_done_rows": q1(c, "select count(*) from self_improvement_log where coalesce(pattern_bridge_status,'')='done'"),
            "negative_learning_rows": q1(c, "select count(*) from learning_results where proposal_id <= -1000000000 and coalesce(success_flag,0)=0"),
            "positive_learning_rows": q1(c, "select count(*) from learning_results where proposal_id <= -1000000000 and coalesce(success_flag,0)=1"),
            "secretary_done_remaining": q1(c, "select count(*) from inbox_commands where coalesce(status,'')='secretary_done'"),
            "tg_private_pending": q1(c, "select count(*) from inbox_commands where coalesce(source,'')='tg_private_chat_log' and coalesce(status,'')='pending'"),
            "manual_pending": q1(c, "select count(*) from inbox_commands where coalesce(source,'')='manual' and coalesce(status,'')='pending'"),
            "ops_exec_new_remaining": q1(c, "select count(*) from router_tasks where coalesce(target_bot,'')='ops_exec' and coalesce(status,'')='new'"),
            "kaikun04_new_remaining": q1(c, "select count(*) from router_tasks where coalesce(target_bot,'')='kaikun04' and coalesce(status,'')='new'"),
            "kaikun04_done_sent_missing": q1(c, """
                select count(*)
                from router_tasks rt
                join inbox_commands ic on ic.id = rt.source_command_id
                where coalesce(rt.target_bot,'')='kaikun04'
                  and coalesce(rt.status,'')='done'
                  and coalesce(ic.router_finish_status,'')='sent'
                  and coalesce(rt.sent_message_id,'')=''
            """),
            "top_exec_patterns": qrows(c, """
                select pattern_key, sample_count, success_count, avg_result_score, weight, updated_at
                from learning_patterns
                where pattern_type='self_improvement_exec'
                order by weight desc, success_count desc, sample_count desc, id desc
                limit 10
            """),
            "top_success_patterns": qrows(c, """
                select pattern, score, updated_at
                from success_patterns
                where pattern like 'script=%'
                order by score desc, updated_at desc
                limit 10
            """),
            "latest_self_improvement_rows": qrows(c, """
                select
                  id,parent_task_id,child_task_id,source_command_id,kind,status,
                  coalesce(learning_bridge_status,'') as learning_bridge_status,
                  coalesce(pattern_bridge_status,'') as pattern_bridge_status,
                  coalesce(learning_result_id,0) as learning_result_id,
                  updated_at
                from self_improvement_log
                order by id desc
                limit 10
            """),
        }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[self_improvement_feedback_metrics_v1] wrote {OUT}", flush=True)

def main():
    while True:
        try:
            collect()
        except Exception as e:
            print(f"[self_improvement_feedback_metrics_v1] err={e!r}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
