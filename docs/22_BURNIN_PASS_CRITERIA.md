# BURN-IN PASS CRITERIA
## Required
- core launchagents stay loaded
- execute_now backlog stays near zero
- pr_open backlog stays near zero
- true_pending_impact stays zero
- ceo_hub_events keeps moving
- no repeating fatal errors in:
  - logs/dev_command_executor_v1.err
  - logs/dev_pr_watcher_v1.err
  - logs/dev_pr_automerge_v1.err
  - logs/dev_merge_notify_v1.err
  - logs/impact_judge_v1.err

## Warning
- proposals generated for archived bots
- source_ai empty in notifications
- repeated DB lock traces
- repeated launchctl bootstrap failures

## Pass view
sqlite3 data/openclaw.db "
select
  count(*) as total,
  sum(case when coalesce(status,'')='approved' and coalesce(dev_stage,'')='execute_now' then 1 else 0 end) as execute_now,
  sum(case when coalesce(status,'')='approved' and coalesce(dev_stage,'')='pr_open' then 1 else 0 end) as pr_open,
  sum(case when coalesce(status,'')='merged' and coalesce(dev_stage,'')='merged' and coalesce(pr_status,'')='merged' then 1 else 0 end) as merged_all
from dev_proposals;
"
