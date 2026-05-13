create table if not exists public_orders (
  id integer primary key autoincrement,
  plan text not null,
  customer_name text not null,
  birth_date text not null,
  birth_time text,
  birth_place text,
  question text not null,
  email text not null,
  created_at text not null
);

create table if not exists public_unlocks (
  id integer primary key autoincrement,
  order_id integer not null,
  price_yen integer not null default 760,
  status text not null default 'pending',
  created_at text not null
);

create table if not exists revenue_page_views (
  id integer primary key autoincrement,
  path text not null,
  event_type text not null default 'page_view',
  variant_id text not null default '',
  traffic_source text not null default '',
  referer text not null default '',
  ua text not null default '',
  ip_hash text not null default '',
  created_at text not null
);
