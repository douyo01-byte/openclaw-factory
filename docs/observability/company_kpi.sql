-- PR / merge / learning / proposal throughput
select 'pr_per_hour' as metric,
round(
  count(*) * 3600.0 /
  nullif(strftime('%s','now') - strftime('%s',min(created_at)), 0),
  4
) as value
from ceo_hub_events
where event_type='pr_created'
union all
select 'merge_per_hour',
round(
  count(*) * 3600.0 /
  nullif(strftime('%s','now') - strftime('%s',min(created_at)), 0),
  4
)
from ceo_hub_events
where event_type='merged'
union all
select 'learning_per_hour',
round(
  count(*) * 3600.0 /
  nullif(strftime('%s','now') - strftime('%s',min(created_at)), 0),
  4
)
from ceo_hub_events
where event_type='learning_result'
union all
select 'proposal_per_hour',
round(
  count(*) * 3600.0 /
  nullif(strftime('%s','now') - strftime('%s',min(created_at)), 0),
  4
)
from dev_proposals
union all
select 'proposal_adoption_rate',
round(
  sum(case when status='approved' then 1 else 0 end) * 1.0 /
  nullif(count(*),0),
  6
)
from dev_proposals
union all
select 'revenue_proposal_count',
count(*)
from dev_proposals
where category='revenue';

-- lifecycle KPI ordered only
with ev as (
  select
    proposal_id,
    max(case when event_type='pr_created' then created_at end) as pr_created_at,
    max(case when event_type='merged' then created_at end) as merged_at,
    max(case when event_type='learning_result' then created_at end) as learning_at
  from ceo_hub_events
  where event_type in ('pr_created','merged','learning_result')
    and proposal_id is not null
  group by proposal_id
),
lifecycle as (
  select
    proposal_id,
    round((julianday(merged_at) - julianday(pr_created_at)) * 86400.0, 1) as pr_to_merge_sec,
    round((julianday(learning_at) - julianday(merged_at)) * 86400.0, 1) as merge_to_learning_sec,
    round((julianday(learning_at) - julianday(pr_created_at)) * 86400.0, 1) as pr_to_learning_sec
  from ev
  where pr_created_at is not null
    and merged_at is not null
    and learning_at is not null
    and julianday(merged_at) >= julianday(pr_created_at)
    and julianday(learning_at) >= julianday(merged_at)
)
select 'avg_pr_to_merge_sec' as metric, round(avg(pr_to_merge_sec),1) as value from lifecycle
union all
select 'avg_merge_to_learning_sec', round(avg(merge_to_learning_sec),1) from lifecycle
union all
select 'avg_pr_to_learning_sec', round(avg(pr_to_learning_sec),1) from lifecycle;

-- duplicate ratio
with dup as (
  select sum(cnt - 1) as dup_rows
  from (
    select count(*) as cnt
    from dev_proposals
    group by title
    having count(*) > 1
  )
),
tot as (
  select count(*) as total_rows from dev_proposals
)
select
  'duplicate_ratio' as metric,
  round(coalesce((select dup_rows from dup),0) * 1.0 / nullif((select total_rows from tot),0), 6) as value;
