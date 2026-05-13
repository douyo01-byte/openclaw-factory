-- OpenClaw router core schema v1
-- Moves router runtime schema mutation into governed migrations.

create table if not exists inbox_commands (
  id integer primary key autoincrement,
  chat_id text not null,
  message_id integer,
  reply_to_message_id integer,
  from_username text,
  from_name text,
  text text not null,
  received_at text default (datetime('now')),
  applied_at text,
  status text default 'new',
  error text
);

create table if not exists router_tasks (
  id integer primary key autoincrement,
  source_command_id integer,
  mode text not null default 'FAST',
  target_bot text not null default 'kaikun04',
  task_text text not null,
  status text not null default 'new',
  created_at text default (datetime('now')),
  updated_at text default (datetime('now'))
);

create table if not exists self_improvement_log (
  id integer primary key autoincrement,
  parent_task_id integer not null,
  child_task_id integer,
  source_command_id integer,
  kind text not null default 'exec_bridge',
  problem text not null default '',
  fix text not null default '',
  result text not null default '',
  reusable_pattern text not null default '',
  created_at text default (datetime('now'))
);

alter table inbox_commands add column source text not null default '';
alter table inbox_commands add column processed integer default 0;
alter table inbox_commands add column router_status text default '';
alter table inbox_commands add column router_target text default '';
alter table inbox_commands add column router_mode text default '';
alter table inbox_commands add column router_finish_status text default '';
alter table inbox_commands add column router_task_id integer default 0;
alter table inbox_commands add column updated_at text default '';

alter table router_tasks add column parent_task_id integer default 0;
alter table router_tasks add column task_role text default '';
alter table router_tasks add column clean_prompt text default '';
alter table router_tasks add column reply_text text default '';
alter table router_tasks add column result_text text default '';
alter table router_tasks add column sent_message_id text default '';
alter table router_tasks add column started_at text default '';
alter table router_tasks add column finished_at text default '';
alter table router_tasks add column validation_status text default '';
alter table router_tasks add column validation_reason text default '';
alter table router_tasks add column retry_count integer default 0;
alter table router_tasks add column exec_bridge_status text default '';
alter table router_tasks add column exec_bridge_reason text default '';
alter table router_tasks add column exec_child_task_id integer default 0;

alter table self_improvement_log add column status text not null default '';
alter table self_improvement_log add column parent_reply_head text not null default '';
alter table self_improvement_log add column child_result_head text not null default '';
alter table self_improvement_log add column applied_at text default '';
alter table self_improvement_log add column updated_at text default '';

create index if not exists idx_router_tasks_status
  on router_tasks(status, target_bot, mode);
create index if not exists idx_self_improvement_child
  on self_improvement_log(child_task_id);
create index if not exists idx_self_improvement_parent
  on self_improvement_log(parent_task_id);
