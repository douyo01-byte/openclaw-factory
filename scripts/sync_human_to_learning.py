import os
import sqlite3

DB_PATH = os.environ.get("OCLAW_DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def score_from_human_action(action_type, action_detail, result):
    text = f"{action_type or ''} {action_detail or ''} {result or ''}"
    score = 0.6
    impact = 0.6
    if "返 信" in text or "返信" in text:
        score = max(score, 0.8)
        impact = max(impact, 0.8)
    if "商 談" in text or "商談" in text:
        score = max(score, 0.9)
        impact = max(impact, 0.9)
    if "成 約" in text or "成約" in text:
        score = 1.0
        impact = 1.0
    if (action_type or "") == "todo_generated":
        score = 0.7
        impact = 0.7
    return score, impact

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

try:
    conn.execute("ALTER TABLE learning_results ADD COLUMN human_action_id INTEGER")
except sqlite3.OperationalError:
    pass

rows = conn.execute(
    """
    select h.*
    from human_actions h
    left join learning_results lr
      on lr.human_action_id = h.id
    where lr.human_action_id is null
    order by h.id asc
    limit 50
    """
).fetchall()

synced = 0

for r in rows:
    proposal_id = r["proposal_id"]
    action_id = r["id"]
    action_type = r["action_type"] or ""
    action_detail = r["action_detail"] or ""
    result = r["result"] or ""
    created_at = r["created_at"] or ""

    result_score, impact_score = score_from_human_action(action_type, action_detail, result)

    human_block = (
        "[HUMAN ACTION]\n"
        f"action_type: {action_type}\n"
        f"action_detail: {action_detail}\n"
        f"result: {result}\n"
        f"logged_at: {created_at}"
    )

    existing = conn.execute(
        "select proposal_id, title, result_note from learning_results where proposal_id=?",
        (proposal_id,),
    ).fetchone()

    if existing:
        base_note = existing["result_note"] or ""
        if "[HUMAN ACTION]" in base_note:
            new_note = base_note
        else:
            new_note = base_note + ("\n\n" if base_note else "") + human_block
        conn.execute(
            """
            update learning_results
            set
              title = coalesce(nullif(title,''), 'human execution result'),
              result_type = ?,
              result_score = ?,
              impact_score = ?,
              result_note = ?,
              human_action_id = ?
            where proposal_id = ?
            """,
            (
                "human_todo" if action_type == "todo_generated" else "human_execution",
                result_score,
                impact_score,
                new_note,
                action_id,
                proposal_id,
            ),
        )
    else:
        conn.execute(
            """
            insert into learning_results (
              proposal_id,
              title,
              result_type,
              result_score,
              impact_score,
              result_note,
              human_action_id,
              created_at
            )
            values (?,?,?,?,?,?,?,datetime('now'))
            """,
            (
                proposal_id,
                "human execution result",
                "human_todo" if action_type == "todo_generated" else "human_execution",
                result_score,
                impact_score,
                human_block,
                action_id,
            ),
        )
    synced += 1

conn.commit()
print(f"synced {synced} human actions")
