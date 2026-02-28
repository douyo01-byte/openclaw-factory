import sqlite3
from bots.dev_gatekeeper import evaluate_risk

DB_PATH = "data/openclaw.db"

def create_proposal(title, description, branch_name=None):
    risk = evaluate_risk()
    branch_name = branch_name or "dev/proposal-temp"
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO dev_proposals (title, description, branch_name, risk_level) VALUES (?, ?, ?, ?)",
        (title, description, branch_name, risk),
    )
    proposal_id = cur.lastrowid
    cur.execute(
        "INSERT INTO dev_events (proposal_id, event_type, payload) VALUES (?, ?, ?)",
        (proposal_id, "created", "{}"),
    )
    conn.commit()
    conn.close()
    return proposal_id, risk
