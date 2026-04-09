create table if not exists money_trials (
  id integer primary key autoincrement,
  theme text not null,
  hypothesis text not null,
  product_type text not null default 'ai_fortune',
  status text not null default 'new',
  phase text not null default 'design',
  priority integer not null default 50,
  attempts integer not null default 0,
  revenue_yen integer not null default 0,
  cost_yen integer not null default 0,
  profit_yen integer not null default 0,
  score integer not null default 0,
  owner_bot text not null default 'money_loop_v1',
  notes text not null default '',
  created_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now'))
);

create table if not exists money_actions (
  id integer primary key autoincrement,
  trial_id integer not null,
  action_type text not null,
  action_text text not null,
  status text not null default 'new',
  artifact_path text not null default '',
  result_text text not null default '',
  created_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now'))
);

create table if not exists money_results (
  id integer primary key autoincrement,
  trial_id integer not null,
  action_id integer,
  metric_type text not null,
  metric_value text not null,
  score_delta integer not null default 0,
  created_at text not null default (datetime('now'))
);

create table if not exists fortune_profiles (
  id integer primary key autoincrement,
  profile_key text not null unique,
  name text not null,
  birth_date text not null,
  birth_time text not null default '',
  birth_place text not null default '',
  created_at text not null default (datetime('now'))
);

create table if not exists fortune_readings (
  id integer primary key autoincrement,
  profile_key text not null,
  question text not null,
  engine_version text not null,
  input_hash text not null,
  output_hash text not null,
  reading_text text not null,
  consistency_score integer not null default 0,
  created_at text not null default (datetime('now'))
);

create index if not exists idx_money_trials_status on money_trials(status, phase, priority desc, id asc);
create index if not exists idx_money_actions_trial on money_actions(trial_id, status, id asc);
create index if not exists idx_money_results_trial on money_results(trial_id, id desc);
create index if not exists idx_fortune_readings_profile on fortune_readings(profile_key, id desc);
