
## Runtime Monitoring
Burn-in observation files:
- obs/burnin_20260313_live/burnin_watch.log
- logs/dev_command_executor_v1.err
- logs/dev_pr_watcher_v1.err
- logs/dev_pr_automerge_v1.err

Database source:
- data/openclaw.db

Queue health check query:
sqlite3 data/openclaw.db " select count(*) total, sum(case when coalesce(status,'')='approved' and coalesce(dev_stage,'')='execute_now' then 1 else 0 end) execute_now, sum(case when coalesce(status,'')='approved' and coalesce(dev_stage,'')='pr_open' then 1 else 0 end) pr_open, sum(case when coalesce(status,'')='merged' and coalesce(dev_stage,'')='merged' and coalesce(pr_status,'')='merged' then 1 else 0 end) merged_all from dev_proposals;:
