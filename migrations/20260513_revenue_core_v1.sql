-- OpenClaw Autonomous Revenue Core v1
-- 目的: すべての自律行動を「利益期待値」に収束させる

create table if not exists revenue_opportunities (
  id integer primary key autoincrement,
  source text not null default 'manual',
  title text not null,
  description text not null default '',
  market text not null default '',
  monetization_type text not null default '',
  expected_profit_score integer not null default 0,
  validation_speed_score integer not null default 0,
  cost_score integer not null default 0,
  automation_score integer not null default 0,
  risk_score integer not null default 0,
  total_score integer not null default 0,
  status text not null default 'new',
  rationale text not null default '',
  created_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now'))
);

create table if not exists revenue_experiments (
  id integer primary key autoincrement,
  opportunity_id integer,
  experiment_type text not null default '',
  title text not null,
  hypothesis text not null default '',
  validation_method text not null default '',
  expected_signal text not null default '',
  expected_cost integer not null default 0,
  expected_validation_hours integer not null default 24,
  status text not null default 'new',
  router_task_id integer,
  artifact_path text not null default '',
  result_summary text not null default '',
  created_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now')),
  foreign key(opportunity_id) references revenue_opportunities(id)
);

create table if not exists revenue_metrics (
  id integer primary key autoincrement,
  experiment_id integer not null,
  metric_name text not null,
  metric_value real not null default 0,
  source text not null default '',
  captured_at text not null default (datetime('now')),
  foreign key(experiment_id) references revenue_experiments(id)
);

create table if not exists revenue_learnings (
  id integer primary key autoincrement,
  experiment_id integer,
  opportunity_id integer,
  learning_type text not null default '',
  summary text not null,
  evidence text not null default '',
  action text not null default '',
  confidence integer not null default 0,
  created_at text not null default (datetime('now')),
  foreign key(experiment_id) references revenue_experiments(id),
  foreign key(opportunity_id) references revenue_opportunities(id)
);

create table if not exists revenue_agent_policy (
  id integer primary key autoincrement,
  agent_name text not null unique,
  role text not null,
  allowed_actions text not null default '',
  forbidden_actions text not null default '',
  policy text not null default '',
  created_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now'))
);

insert or ignore into revenue_agent_policy
(agent_name, role, allowed_actions, forbidden_actions, policy)
values
('kaikun04', 'CEO_REVENUE_BRAIN', 'prioritize,plan,route,judge', 'run_unprofitable_loops_without_reason', '全タスクを利益期待値・検証速度・コスト・自動化可能性で評価する'),
('codex', 'BUILDER', 'edit_code,write_tests,run_safe_commands,prepare_patch', 'deploy_without_test_or_policy', '実装・修正・テストを担当する'),
('claude', 'REVIEWER', 'review_design,review_code,find_risks,propose_improvements', 'execute_or_deploy', '設計レビュー・コードレビュー・利益構造レビューのみ担当する');
