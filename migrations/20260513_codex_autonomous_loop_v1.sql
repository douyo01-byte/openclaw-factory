-- OpenClaw Codex autonomous task loop v1
-- Local task execution bridge. It saves prompts/results only; commit/push are not automated.

create table if not exists codex_tasks (
  id integer primary key autoincrement,
  title text not null default '',
  task_text text not null,
  status text not null default 'new',
  priority integer not null default 0,
  dry_run integer not null default 1,
  timeout_seconds integer not null default 1800,
  prompt_text text not null default '',
  result_summary text not null default '',
  created_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now'))
);

create table if not exists codex_task_runs (
  id integer primary key autoincrement,
  task_id integer not null,
  status text not null default 'running',
  dry_run integer not null default 1,
  prompt_text text not null default '',
  result_summary text not null default '',
  error_text text not null default '',
  started_at text not null default (datetime('now')),
  finished_at text not null default '',
  elapsed_seconds real not null default 0,
  foreign key(task_id) references codex_tasks(id)
);
