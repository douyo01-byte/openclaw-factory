-- OpenClaw Autonomous Revenue Core v1
-- 目的: すべての自律行動を「利益期待値」に収束させる

create table if not exists revenue_opportunities (
  id integer primary key autoincrement,
  source text not null default 'manual',
  domain_key text not null default 'general',
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

create table if not exists revenue_variant_groups (
  id integer primary key autoincrement,
  opportunity_id integer,
  experiment_id integer,
  name text not null default '',
  strategy text not null default 'epsilon_greedy',
  status text not null default 'active',
  winner_experiment_id integer,
  digest_summary text not null default '',
  created_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now')),
  foreign key(opportunity_id) references revenue_opportunities(id),
  foreign key(experiment_id) references revenue_experiments(id),
  foreign key(winner_experiment_id) references revenue_experiments(id)
);

create table if not exists revenue_variant_metrics (
  id integer primary key autoincrement,
  group_id integer not null,
  experiment_id integer not null,
  variant_key text not null default '',
  artifact_path text not null default '',
  views integer not null default 0,
  clicks integer not null default 0,
  telegram_clicks integer not null default 0,
  actions integer not null default 0,
  conversions integer not null default 0,
  ctr real not null default 0,
  cvr real not null default 0,
  score real not null default 0,
  rank integer not null default 0,
  status text not null default 'active',
  source text not null default '',
  captured_at text not null default (datetime('now')),
  unique(group_id, experiment_id),
  foreign key(group_id) references revenue_variant_groups(id),
  foreign key(experiment_id) references revenue_experiments(id)
);

create table if not exists revenue_variant_loser_archive (
  id integer primary key autoincrement,
  group_id integer not null,
  experiment_id integer not null,
  variant_key text not null default '',
  artifact_path text not null default '',
  score real not null default 0,
  reason text not null default '',
  archived_at text not null default (datetime('now')),
  unique(group_id, experiment_id),
  foreign key(group_id) references revenue_variant_groups(id),
  foreign key(experiment_id) references revenue_experiments(id)
);

create table if not exists revenue_bandit_digests (
  id integer primary key autoincrement,
  group_id integer not null,
  summary text not null,
  sent_to_telegram integer not null default 0,
  created_at text not null default (datetime('now')),
  foreign key(group_id) references revenue_variant_groups(id)
);

create table if not exists revenue_distribution_tasks (
  id integer primary key autoincrement,
  group_id integer not null,
  experiment_id integer not null,
  variant_key text not null default '',
  distribution_type text not null,
  traffic_source text not null default '',
  cta_url text not null default '',
  content text not null default '',
  artifact_path text not null default '',
  status text not null default 'planned',
  created_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now')),
  unique(group_id, experiment_id, distribution_type),
  foreign key(group_id) references revenue_variant_groups(id),
  foreign key(experiment_id) references revenue_experiments(id)
);

create table if not exists revenue_distribution_publish_queue (
  id integer primary key autoincrement,
  distribution_task_id integer not null unique,
  group_id integer not null,
  experiment_id integer not null,
  variant_key text not null default '',
  distribution_type text not null default '',
  traffic_source text not null default '',
  artifact_path text not null default '',
  candidate_score real not null default 0,
  publish_status text not null default 'queued',
  approval_note text not null default '',
  queued_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now')),
  foreign key(distribution_task_id) references revenue_distribution_tasks(id)
);

create table if not exists revenue_memory_patterns (
  id integer primary key autoincrement,
  memory_type text not null,
  pattern text not null,
  horizon_type text not null default 'mid_term',
  economic_summary text not null default '',
  portfolio_summary text not null default '',
  domain_summary text not null default '',
  evidence text not null default '',
  score real not null default 1,
  reuse_count integer not null default 0,
  last_used_at text not null default '',
  created_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now')),
  unique(memory_type, pattern)
);

create table if not exists revenue_economic_metrics (
  id integer primary key autoincrement,
  group_id integer not null,
  experiment_id integer not null,
  estimated_cac real not null default 0,
  estimated_ltv real not null default 0,
  payback_speed real not null default 0,
  infra_cost real not null default 0,
  human_cost real not null default 0,
  automation_savings real not null default 0,
  expected_profit real not null default 0,
  profit_efficiency real not null default 0,
  economic_multiplier real not null default 1,
  suppressed integer not null default 0,
  source text not null default '',
  captured_at text not null default (datetime('now')),
  unique(group_id, experiment_id),
  foreign key(group_id) references revenue_variant_groups(id),
  foreign key(experiment_id) references revenue_experiments(id)
);

create table if not exists revenue_real_orders (
  id integer primary key autoincrement,
  group_id integer not null,
  experiment_id integer not null,
  variant_key text not null default '',
  order_id text not null,
  revenue real not null default 0,
  gross_profit real not null default 0,
  refund_risk real not null default 0,
  fulfillment_cost real not null default 0,
  support_cost real not null default 0,
  net_profit real not null default 0,
  recovered_days real not null default 0,
  source text not null default 'local_ingest',
  created_at text not null default (datetime('now')),
  unique(order_id),
  foreign key(group_id) references revenue_variant_groups(id),
  foreign key(experiment_id) references revenue_experiments(id)
);

create table if not exists revenue_capital_allocations (
  id integer primary key autoincrement,
  opportunity_id integer not null unique,
  allocated_budget real not null default 0,
  allocated_compute real not null default 0,
  allocated_time real not null default 0,
  expected_roi real not null default 0,
  realized_roi real not null default 0,
  capital_score real not null default 0,
  risk_score real not null default 0,
  liquidity_score real not null default 100,
  source text not null default 'local_simulation',
  updated_at text not null default (datetime('now')),
  foreign key(opportunity_id) references revenue_opportunities(id)
);

create table if not exists revenue_business_domains (
  id integer primary key autoincrement,
  domain_key text not null unique,
  domain_type text not null default '',
  capital_allocated real not null default 0,
  revenue_generated real not null default 0,
  net_profit real not null default 0,
  volatility_score real not null default 0,
  scalability_score real not null default 50,
  automation_fit real not null default 50,
  moat_score real not null default 0,
  source text not null default 'local_simulation',
  updated_at text not null default (datetime('now'))
);

create table if not exists revenue_capital_migrations (
  id integer primary key autoincrement,
  from_domain text not null,
  to_domain text not null,
  migration_reason text not null default '',
  migrated_budget real not null default 0,
  migrated_compute real not null default 0,
  expected_gain real not null default 0,
  realized_gain real not null default 0,
  migration_score real not null default 0,
  source text not null default 'local_simulation',
  created_at text not null default (datetime('now')),
  unique(from_domain, to_domain, migration_reason)
);

create table if not exists revenue_strategy_scores (
  id integer primary key autoincrement,
  group_id integer not null,
  experiment_id integer not null,
  horizon_type text not null,
  ctr_score real not null default 0,
  conversion_score real not null default 0,
  approval_score real not null default 0,
  revenue_efficiency real not null default 0,
  automation_score real not null default 0,
  sustainability_score real not null default 0,
  total_score real not null default 0,
  source text not null default '',
  captured_at text not null default (datetime('now')),
  unique(group_id, experiment_id, horizon_type),
  foreign key(group_id) references revenue_variant_groups(id),
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
