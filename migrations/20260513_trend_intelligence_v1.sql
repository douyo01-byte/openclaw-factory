-- OpenClaw Trend Intelligence v1
-- GitHub-only proposal queue. No install, execute, deploy, or commit automation.

create table if not exists trend_items (
  id integer primary key autoincrement,
  source text not null default 'github',
  external_id text not null default '',
  title text not null default '',
  url text not null,
  github_url text not null default '',
  repo_full_name text not null default '',
  owner text not null default '',
  description text not null default '',
  language text not null default '',
  license_key text not null default '',
  stars integer not null default 0,
  forks integer not null default 0,
  open_issues integer not null default 0,
  pushed_at text not null default '',
  created_at_source text not null default '',
  raw_json text not null default '',
  safety_status text not null default 'pending',
  first_seen_at text not null default (datetime('now')),
  last_seen_at text not null default (datetime('now')),
  unique(source, url)
);

create table if not exists trend_scores (
  id integer primary key autoincrement,
  item_id integer not null unique,
  usefulness_score real not null default 0,
  reuse_score real not null default 0,
  license_score real not null default 0,
  star_velocity_score real not null default 0,
  maintenance_score real not null default 0,
  safety_score real not null default 0,
  noise_penalty real not null default 0,
  total_score real not null default 0,
  score_reason text not null default '',
  scored_at text not null default (datetime('now'))
);

create table if not exists trend_proposals (
  id integer primary key autoincrement,
  item_id integer not null unique,
  proposal_status text not null default 'queued',
  candidate_score real not null default 0,
  proposal_title text not null default '',
  proposal_summary text not null default '',
  safety_summary text not null default '',
  next_prompt text not null default '',
  approval_required integer not null default 1,
  created_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now'))
);

create index if not exists idx_trend_items_repo
  on trend_items(repo_full_name, last_seen_at);

create index if not exists idx_trend_proposals_status_score
  on trend_proposals(proposal_status, candidate_score);
