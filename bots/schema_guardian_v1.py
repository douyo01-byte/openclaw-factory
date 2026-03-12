import os, sqlite3, time

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

DEV_PROPOSALS = [
    ("processing","INTEGER DEFAULT 0"),
    ("spec","TEXT DEFAULT ''"),
    ("project_decision","TEXT DEFAULT ''"),
    ("dev_stage","TEXT DEFAULT ''"),
    ("pr_status","TEXT DEFAULT ''"),
    ("pr_url","TEXT DEFAULT ''"),
    ("pr_number","INTEGER"),
    ("spec_stage","TEXT DEFAULT ''"),
    ("category","TEXT DEFAULT ''"),
    ("target_system","TEXT DEFAULT ''"),
    ("improvement_type","TEXT DEFAULT ''"),
    ("quality_score","REAL DEFAULT 0"),
    ("result_type","TEXT DEFAULT ''"),
    ("priority","INTEGER DEFAULT 0"),
    ("guard_status","TEXT DEFAULT ''"),
    ("guard_reason","TEXT DEFAULT ''"),
    ("decision_note","TEXT DEFAULT ''"),
    ("score","REAL DEFAULT 0"),
]

TABLES = {
    "proposal_conversation": """
CREATE TABLE IF NOT EXISTS proposal_conversation (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  proposal_id INTEGER,
  role TEXT,
  message TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""",
    "proposal_state": """
CREATE TABLE IF NOT EXISTS proposal_state (
  proposal_id INTEGER PRIMARY KEY,
  stage TEXT,
  pending_questions TEXT,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""",
    "decision_patterns": """
CREATE TABLE IF NOT EXISTS decision_patterns (
  token TEXT PRIMARY KEY,
  weight REAL NOT NULL,
  updated_at TEXT DEFAULT (datetime('now'))
)
""",
}

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_dev_proposals_status ON dev_proposals(status)",
    "CREATE INDEX IF NOT EXISTS idx_dev_proposals_pipeline ON dev_proposals(status, dev_stage, pr_status)",
    "CREATE INDEX IF NOT EXISTS idx_dev_proposals_pr_number ON dev_proposals(pr_number)",
    "CREATE INDEX IF NOT EXISTS idx_dev_proposals_pr_url ON dev_proposals(pr_url)",
]

def patch():
    con = sqlite3.connect(DB, timeout=30)
    con.execute("pragma busy_timeout=30000")
    cur = con.cursor()

    cur.execute("""
CREATE TABLE IF NOT EXISTS dev_proposals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  description TEXT,
  branch_name TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'pending',
  risk_level TEXT NOT NULL DEFAULT 'medium',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

    cols = {r[1] for r in cur.execute("pragma table_info(dev_proposals)")}
    for name, ddl in DEV_PROPOSALS:
        if name not in cols:
            cur.execute(f"ALTER TABLE dev_proposals ADD COLUMN {name} {ddl}")

    for sql in TABLES.values():
        cur.execute(sql)

    for sql in INDEXES:
        cur.execute(sql)

    con.commit()
    con.close()

while True:
    try:
        patch()
        print("schema_guardian_ok", flush=True)
    except Exception as e:
        print(repr(e), flush=True)
    time.sleep(30)
