import sqlite3

DDL = """
CREATE TABLE IF NOT EXISTS dev_proposals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  description TEXT,
  branch_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  risk_level TEXT NOT NULL DEFAULT 'medium',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_dev_proposals_status ON dev_proposals(status);

CREATE TABLE IF NOT EXISTS dev_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  proposal_id INTEGER NOT NULL,
  event_type TEXT NOT NULL,
  payload TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (proposal_id) REFERENCES dev_proposals(id)
);
CREATE INDEX IF NOT EXISTS idx_dev_events_proposal ON dev_events(proposal_id);
"""

def apply(db_path="data/openclaw.db"):
    conn = sqlite3.connect(db_path)
    conn.executescript(DDL)
    conn.commit()
    conn.close()
