-- Revenue exec router schema readiness v1
-- Minimal columns required by bots/revenue_exec_router_v1.py on legacy revenue tables.

alter table revenue_variant_metrics
  add column telegram_clicks integer not null default 0;

alter table revenue_variant_metrics
  add column ctr real not null default 0;

alter table revenue_variant_metrics
  add column cvr real not null default 0;

alter table revenue_distribution_tasks
  add column artifact_path text not null default '';
