import os, sqlite3, time
from datetime import datetime

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
LOG = "logs/ceo_terminal_executor_guarded_normalizer_v1.out"

def run():
    con = sqlite3.connect(DB, timeout=30)
    con.execute("pragma busy_timeout=30000")
    cur = con.cursor()
    rows = cur.execute("""
        select id, coalesce(priority,0), coalesce(project_decision,''), coalesce(decision_note,'')
        from dev_proposals
        where coalesce(source_ai,'')='ceo_terminal_executor_guarded_promoter_v1'
          and coalesce(status,'')='new'
        order by id desc
        limit 50
    """).fetchall()
    n = 0
    for pid, priority, decision, note in rows:
        new_priority = 85 if "priority_fixed_85" in note or "terminal_executor_priority_fixed_85" in note else int(priority or 0)
        if new_priority < 85:
            new_priority = 85
        new_note = note
        if "terminal_guard_ready" not in new_note:
            new_note = (new_note + " | terminal_guard_ready").strip(" |")
        cur.execute("""
            update dev_proposals
            set priority=?,
                project_decision=case when coalesce(project_decision,'')='' then 'go' else project_decision end,
                decision_note=?
            where id=?
        """, (new_priority, new_note, pid))
        n += cur.rowcount
    con.commit()
    con.close()
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} normalized={n}\n")

while True:
    try:
        run()
    except Exception as e:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} error={e}\n")
    time.sleep(60)
