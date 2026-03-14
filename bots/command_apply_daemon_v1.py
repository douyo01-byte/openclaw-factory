import os
import re
import sqlite3
import time

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    return c

def parse(text: str):
    t = (text or "").strip()
    m = re.search(r"(承認|approve|保留|hold|却下|reject)\s*#?\s*(\d+)", t, re.I)
    if not m:
        return None, None
    act = m.group(1).lower()
    pid = int(m.group(2))
    if act in ("承認", "approve"):
        return "approve", pid
    if act in ("保留", "hold"):
        return "hold", pid
    return "reject", pid

def run_once():
    c = conn()
    try:
        rows = c.execute("""
            select id, chat_id, text
            from inbox_commands
            where coalesce(processed,0)=0
            order by id asc
            limit 20
        """).fetchall()
        done = 0
        for r in rows:
            act, pid = parse(r["text"] or "")
            if not act:
                continue
            row = c.execute("select id from dev_proposals where id=?", (pid,)).fetchone()
            if not row:
                c.execute("""
                    update inbox_commands
                    set processed=1,status='command_error',applied_at=datetime('now'),error='proposal_not_found'
                    where id=?
                """, (int(r["id"]),))
                done += 1
                continue
            if act == "approve":
                c.execute("""
                    update dev_proposals
                    set status='approved',
                        project_decision='execute_now',
                        dev_stage=case when coalesce(dev_stage,'')='' then 'execute_now' else dev_stage end,
                        guard_status=case when coalesce(guard_status,'')='' then 'safe' else guard_status end,
                        decision_note='CEO approve'
                    where id=?
                """, (pid,))
                st = "command_applied"
            elif act == "hold":
                c.execute("""
                    update dev_proposals
                    set guard_status='hold',
                        decision_note='CEO hold'
                    where id=?
                """, (pid,))
                st = "command_applied"
            else:
                c.execute("""
                    update dev_proposals
                    set status='closed',
                        project_decision='rejected',
                        dev_stage='closed',
                        decision_note='CEO reject'
                    where id=?
                """, (pid,))
                st = "command_applied"
            c.execute("""
                update inbox_commands
                set processed=1,status=?,applied_at=datetime('now'),error=''
                where id=?
            """, (st, int(r["id"])))
            done += 1
        c.commit()
        print(f"command_apply_done={done}", flush=True)
    finally:
        c.close()

if __name__ == "__main__":
    while True:
        try:
            run_once()
        except Exception as e:
            print(f"command_apply_error={e!r}", flush=True)
        time.sleep(5)
