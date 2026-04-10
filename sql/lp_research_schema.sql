create table if not exists lp_sources (
  id integer primary key autoincrement,
  url text not null unique,
  niche text not null default '',
  source_type text not null default 'manual',
  status text not null default 'new',
  fetched_at text not null default '',
  created_at text not null default (datetime('now'))
);

create table if not exists lp_pages (
  id integer primary key autoincrement,
  source_id integer not null,
  url text not null,
  title text not null default '',
  raw_text text not null default '',
  html_path text not null default '',
  text_path text not null default '',
  created_at text not null default (datetime('now'))
);

create table if not exists lp_patterns (
  id integer primary key autoincrement,
  source_id integer not null,
  hook text not null default '',
  problem text not null default '',
  promise text not null default '',
  proof text not null default '',
  cta text not null default '',
  price_hint text not null default '',
  notes text not null default '',
  score integer not null default 0,
  created_at text not null default (datetime('now'))
);

create table if not exists lp_rewrites (
  id integer primary key autoincrement,
  niche text not null,
  input_context text not null default '',
  output_path text not null default '',
  score integer not null default 0,
  created_at text not null default (datetime('now'))
);

create index if not exists idx_lp_sources_status on lp_sources(status, niche, id);
create index if not exists idx_lp_patterns_source on lp_patterns(source_id, score desc, id desc);
