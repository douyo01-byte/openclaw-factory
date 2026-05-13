-- OpenClaw migration ledger v1
-- Tracks applied SQLite migrations and their content hashes.

create table if not exists openclaw_migration_ledger (
  id integer primary key autoincrement,
  migration_name text not null unique,
  file_path text not null default '',
  sha256 text not null default '',
  status text not null default 'applied',
  applied_at text not null default (datetime('now')),
  applied_by text not null default '',
  db_path text not null default '',
  error_text text not null default ''
);

create index if not exists idx_openclaw_migration_ledger_status
  on openclaw_migration_ledger(status, applied_at);
