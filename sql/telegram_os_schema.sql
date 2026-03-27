create table if not exists conversation_jobs (
  id integer primary key autoincrement,
  source_chat_id text,
  source_message_id text,
  domain text not null,
  request_text text not null,
  target_object text,
  current_phase text not null default 'received',
  status text not null default 'new',
  assigned_ai text,
  parent_job_id integer,
  created_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now'))
);

create table if not exists conversation_job_steps (
  id integer primary key autoincrement,
  job_id integer not null,
  step_type text not null,
  step_order integer not null,
  status text not null default 'new',
  input_json text,
  output_json text,
  created_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now'))
);

create table if not exists conversation_artifacts (
  id integer primary key autoincrement,
  job_id integer not null,
  artifact_type text not null,
  artifact_title text,
  artifact_body text,
  artifact_path text,
  version integer not null default 1,
  created_at text not null default (datetime('now'))
);
