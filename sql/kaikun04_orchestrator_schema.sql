create table if not exists kaikun04_orchestrator_runs (
  id integer primary key autoincrement,
  task_text text not null,
  mode text,
  target_system text,
  context_json text,
  planner_backend text not null default 'heuristic',
  plan_json text not null,
  created_at text not null default (datetime('now'))
);

create index if not exists idx_kaikun04_orchestrator_runs_created_at
on kaikun04_orchestrator_runs(created_at);

create index if not exists idx_kaikun04_orchestrator_runs_target_system
on kaikun04_orchestrator_runs(target_system);
