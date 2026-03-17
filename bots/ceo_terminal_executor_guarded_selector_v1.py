import os, sqlite3, time
from datetime import datetime
from pathlib import Path

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
REPORT = Path("reports/audit_20260317/ceo_terminal_executor_guarded_selection.md")
LOG = "logs/ceo_terminal_executor_guarded_selector_v1.out"

def score_row(priority, note):
    s = int(priority or 0)
    if "terminal_guard_ready" in note:
        s += 30
    if "terminal_executor_selected" in note:
        s += 15
    if "terminal_executor_priority_fixed_85" in note:
        s += 15
    if "selected_for_execution" in note:
        s += 5
    return s

def run():
    con = sqlite3.connect(DB, timeout=30)
    con.execute("pragma busy_timeout=30000")
    cur = con.cursor()
    rows = cur.execute("""
        select
          id,
          coalesce(title,''),
          coalesce(source_ai,''),
          coalesce(priority,0),
          coalesce(target_system,''),
          coalesce(improvement_type,''),
          coalesce(project_decision,''),
          coalesce(decision_note,''),
          coalesce(created_at,'')
        from dev_proposals
        where coalesce(source_ai,'')='ceo_terminal_executor_guarded_promoter_v1'
          and coalesce(status,'')='new'
        order by id desc
        limit 20
    """).fetchall()

    ranked = []
    for r in rows:
        pid, title, source_ai, priority, target_system, improvement_type, project_decision, note, created_at = r
        ranked.append((score_row(priority, note),) + r)
    ranked.sort(reverse=True)

    selected = None
    for row in ranked:
        score, pid, title, source_ai, priority, target_system, improvement_type, project_decision, note, created_at = row
        if int(priority or 0) >= 85 and "terminal_guard_selected" not in note:
            selected = row
            new_note = note
            if "terminal_guard_selected" not in new_note:
                new_note = (new_note + " | terminal_guard_selected").strip(" |")
            cur.execute("""
                update dev_proposals
                set project_decision='selected_now',
                    decision_note=?
                where id=?
            """, (new_note, pid))
            break

    con.commit()
    con.close()

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# CEO Terminal Executor Guarded Selection ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"]
    if selected:
        score, pid, title, source_ai, priority, target_system, improvement_type, project_decision, note, created_at = selected
        lines += [
            f"- selected_id: {pid}",
            f"- selection_score: {score}",
            f"- source_ai: {source_ai}",
            f"- title: {title}",
            f"- target_system: {target_system}",
            f"- improvement_type: {improvement_type}",
            f"- priority: {priority}",
            f"- decision_note: {note} | terminal_guard_selected",
            f"- created_at: {created_at}",
        ]
    else:
        lines += ["- selected_id: none"]
    lines += [
        "| rank | score | id | source_ai | priority | title |",
        "|---:|---:|---:|---|---:|---|",
    ]
    for i, row in enumerate(ranked, 1):
        score, pid, title, source_ai, priority, target_system, improvement_type, project_decision, note, created_at = row
        lines.append(f"| {i} | {score} | {pid} | {source_ai} | {priority} | {title} |")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} ranked={len(ranked)}\n")

while True:
    try:
        run()
    except Exception as e:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} error={e}\n")
    time.sleep(60)
