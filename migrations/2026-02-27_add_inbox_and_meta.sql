BEGIN;

CREATE TABLE IF NOT EXISTS inbox_commands (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chat_id TEXT NOT NULL,
  message_id INTEGER,
  reply_to_message_id INTEGER,
  from_username TEXT,
  from_name TEXT,
  text TEXT NOT NULL,
  received_at TEXT DEFAULT (datetime('now')),
  applied_at TEXT,
  status TEXT DEFAULT 'new',
  error TEXT
);

CREATE TABLE IF NOT EXISTS retrospectives (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chat_id TEXT NOT NULL,
  from_username TEXT,
  text TEXT NOT NULL,
  received_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS item_meta (
  item_id INTEGER PRIMARY KEY,
  decision TEXT,
  priority INTEGER DEFAULT 0,
  score_market INTEGER DEFAULT 0,
  score_profit INTEGER DEFAULT 0,
  note TEXT,
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS bot_state (
  k TEXT PRIMARY KEY,
  v TEXT
);

COMMIT;
