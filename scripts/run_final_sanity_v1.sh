#!/bin/bash
set -euo pipefail
DB="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

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
echo '===== AI EMPLOYEE SANITY ====='
sqlite3 -cmd ".headers on" -cmd ".mode column" "$DB" "
select count(*) as ai_employee_scores_count from ai_employee_scores;
select count(*) as ai_employee_rankings_count from ai_employee_rankings;
select rank_no, source_ai, total_count, merged_count, round(merge_rate,4) as merge_rate, round(score,4) as score
from ai_employee_rankings
order by rank_no asc
limit 10;
"

echo
echo '===== SECRETARY ROUTE CHECK ====='
grep -n 'return "ai_employee_ranking"\|elif route == "ai_employee_ranking"\|return "runtime_classification"\|elif route == "runtime_classification"' bots/secretary_llm_v1.py || true

echo
echo '===== KAIKUN02 ROUTE CHECK ====='
grep -n 'quick_ai_employee_ranking\|quick_ai_employee_ranking_sent\|quick_runtime_classification\|quick_runtime_classification_sent' bots/kaikun02_router_worker_v1.py || true

echo
echo '===== WORKTREE ====='
git status --short
