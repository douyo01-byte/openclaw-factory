import os, sqlite3, re
from datetime import datetime

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
ROOT = "/Users/doyopc/AI/openclaw-factory-daemon"
LOG = f"{ROOT}/logs/ceo_terminal_guard_bridge_v1.out"

def now():
    return datetime.now().isoformat(timespec="seconds")

def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} {msg}\n")

def make_branch_name(target_system: str, src_id: int, created_at: str) -> str:
    ts = re.sub(r"[^0-9]", "", created_at or "")[:14]
    if not ts:
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
    target = re.sub(r"[^a-zA-Z0-9_/-]", "-", target_system or "unknown")
    return f"ceo-terminal-guard/{target}-{src_id}-{ts}"

def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    c = con.cursor()

    row = c.execute("""
        select
          id, title, source_ai, status,
          coalesce(priority,0) as priority,
          coalesce(project_decision,'') as project_decision,
          coalesce(decision_note,'') as decision_note,
          coalesce(target_system,'') as target_system,
          coalesce(improvement_type,'') as improvement_type,
          coalesce(branch_name,'') as branch_name,
          coalesce(created_at,'') as created_at
        from dev_proposals
        where source_ai='ceo_terminal_executor_guarded_promoter_v1'
          and coalesce(project_decision,'')='selected_now'
          and coalesce(decision_note,'') like '%terminal_guard_selected%'
          and coalesce(decision_note,'') not like '%terminal_guard_bridged%'
        order by cast(coalesce(priority,0) as integer) desc, id desc
        limit 1
    """).fetchone()

    if not row:
        log("bridged=0")
        con.close()
        return

    branch_name = row["branch_name"].strip() or make_branch_name(row["target_system"], row["id"], row["created_at"])
    new_note = row["decision_note"] + " | terminal_guard_from=" + str(row["id"])

    c.execute("""
        insert into dev_proposals (
          title, source_ai, status, priority, project_decision,
          decision_note, target_system, improvement_type,
          branch_name, created_at
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "Executor最終実行ガード本流投入 : " + row["title"],
        "ceo_terminal_guard_bridge_v1",
        "new",
        int(row["priority"] or 0),
        "go",
        new_note,
        row["target_system"],
        row["improvement_type"],
        branch_name,
        now()
    ))

    c.execute("""
        update dev_proposals
        set decision_note = case
          when coalesce(decision_note,'') like '%terminal_guard_bridged%'
            then coalesce(decision_note,'')
          else coalesce(decision_note,'') || ' | terminal_guard_bridged'
        end
        where id=?
    """, (row["id"],))

    con.commit()
    log(f"bridged=1 source={row['id']}")
    con.close()

if __name__ == "__main__":
    main()
