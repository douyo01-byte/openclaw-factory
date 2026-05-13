-- OpenClaw Unified Runtime Digest v1
-- Stores optional low-noise runtime digest snapshots. Sending is intentionally out of scope.

create table if not exists unified_runtime_digests (
  id integer primary key autoincrement,
  digest_type text not null default 'dry_run',
  window_minutes integer not null default 60,
  summary text not null default '',
  execution_section text not null default '',
  runtime_health_section text not null default '',
  cleanup_section text not null default '',
  codex_section text not null default '',
  revenue_section text not null default '',
  trend_section text not null default '',
  risk_section text not null default '',
  sent_to_telegram integer not null default 0,
  created_at text not null default (datetime('now'))
);

create table if not exists unified_runtime_digest_state (
  key text primary key,
  value text not null default '',
  updated_at text not null default (datetime('now'))
);

create index if not exists idx_unified_runtime_digests_created
  on unified_runtime_digests(created_at, digest_type);
