-- OpenClaw Revenue Core schema v2
-- Moves Revenue runtime schema additions into migration governance.

alter table revenue_opportunities
  add column domain_key text not null default 'general';

alter table revenue_variant_metrics
  add column telegram_clicks integer not null default 0;

alter table revenue_variant_metrics
  add column ctr real not null default 0;

alter table revenue_variant_metrics
  add column cvr real not null default 0;

alter table revenue_distribution_tasks
  add column artifact_path text not null default '';

create table if not exists revenue_variant_loser_archive (
  id integer primary key autoincrement,
  group_id integer not null,
  experiment_id integer not null,
  variant_key text not null default '',
  artifact_path text not null default '',
  score real not null default 0,
  reason text not null default '',
  archived_at text not null default (datetime('now')),
  unique(group_id, experiment_id)
);

create table if not exists revenue_bandit_digests (
  id integer primary key autoincrement,
  group_id integer not null,
  summary text not null,
  sent_to_telegram integer not null default 0,
  created_at text not null default (datetime('now'))
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
  updated_at text not null default (datetime('now'))
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
  unique(group_id, experiment_id, horizon_type)
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
  unique(group_id, experiment_id)
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
  unique(order_id)
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
  updated_at text not null default (datetime('now'))
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
