create table if not exists lp_variants (
  id integer primary key autoincrement,
  variant text not null unique,
  niche text not null default '恋愛',
  page_path text not null,
  status text not null default 'candidate',
  views integer not null default 0,
  unlocks integer not null default 0,
  score integer not null default 0,
  created_at text not null default (datetime('now'))
);
