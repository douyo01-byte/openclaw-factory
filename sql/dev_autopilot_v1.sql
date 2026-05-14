create table if not exists dev_autopilot_queue (
  id integer primary key autoincrement,
  status text not null default 'new'
    check (status in ('new', 'running', 'review', 'approved', 'failed', 'done', 'deferred')),
  execution_type text not null default 'dry-run'
    check (execution_type in ('observation', 'dry-run', 'code_change', 'db_update')),
  dry_run integer not null default 1,
  priority integer not null default 50,
  task_text text not null,
  safety_rules text not null default '',
  target_files text not null default '',
  suggested_commands text not null default '',
  result_summary text not null default '',
  source_table text not null default '',
  source_id integer not null default 0,
  created_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now'))
);

create index if not exists idx_dev_autopilot_queue_pick
  on dev_autopilot_queue(status, dry_run, priority, id);

create index if not exists idx_dev_autopilot_queue_source
  on dev_autopilot_queue(source_table, source_id);
