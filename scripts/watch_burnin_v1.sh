#!/bin/bash
set -euo pipefail
DB="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
while true
do
  clear
  date
  echo
  echo '===== FINAL SANITY ====='
  sqlite3 -cmd ".headers on" -cmd ".mode column" "$DB" "
  select
    sum(case when coalesce(pr_status,'')='open' and coalesce(pr_url,'')<>'' then 1 else 0 end) as open_pr_count,
    sum(case when trim(coalesce(source_ai,''))='' then 1 else 0 end) as blank_source_ai,
    sum(case when coalesce(result_type,'')='' and coalesce(status,'')='merged' and coalesce(dev_stage,'')='merged' and coalesce(pr_status,'')='merged' then 1 else 0 end) as merged_without_result_type,
    sum(case
      when coalesce(status,'')='approved' then 0
      when coalesce(status,'')='throttled' then 0
      when coalesce(status,'')='blocked_target_policy' then 0
      when coalesce(dev_stage,'')='backlog' then 0
      when coalesce(status,'')='merged' and (coalesce(dev_stage,'')<>'merged' or coalesce(pr_status,'')<>'merged') then 1
      when coalesce(pr_status,'')='merged' and (coalesce(status,'')<>'merged' or coalesce(dev_stage,'')<>'merged') then 1
      else 0
    end) as stage_divergence_count
  from dev_proposals;
  "
  echo
  echo '===== ROUTER TASKS ====='
  sqlite3 -cmd ".headers on" -cmd ".mode column" "$DB" "
  select coalesce(status,''), count(*)
  from router_tasks
  group by coalesce(status,'')
  order by 1;
  "
  echo
  echo '===== AI EMPLOYEE TOP5 ====='
  sqlite3 -cmd ".headers on" -cmd ".mode column" "$DB" "
  select rank_no, source_ai, total_count, merged_count
  from ai_employee_rankings
  order by rank_no asc
  limit 5;
  "
  echo
  echo '===== WORKTREE ====='
  git -C /Users/doyopc/AI/openclaw-factory-daemon status --short
  sleep 30
done
