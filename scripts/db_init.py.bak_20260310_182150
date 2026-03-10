import sqlite3
from pathlib import Path

db = Path("data/openclaw.db")
db.parent.mkdir(parents=True, exist_ok=True)

con = sqlite3.connect(db)
cur = con.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT UNIQUE,
  title TEXT,
  source TEXT,
  first_seen_at TEXT DEFAULT (datetime('now')),
  last_seen_at TEXT DEFAULT (datetime('now')),
  status TEXT DEFAULT 'new'
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS reviews (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT,
  decision TEXT,           -- good/bad/hold
  note TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);
""")

con.commit()
con.close()
print("OK: data/openclaw.db initialized")
