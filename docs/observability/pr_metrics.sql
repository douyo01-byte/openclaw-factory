-- lifecycle base
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
    pr_created_at,
    merged_at,
    learning_at,
    cast((julianday(merged_at) - julianday(pr_created_at)) * 86400 as integer) as pr_to_merge_sec,
    cast((julianday(learning_at) - julianday(merged_at)) * 86400 as integer) as merge_to_learning_sec,
    cast((julianday(learning_at) - julianday(pr_created_at)) * 86400 as integer) as pr_to_learning_sec
  from ev
)

-- latest lifecycle
select
  proposal_id,
  pr_created_at,
  merged_at,
  learning_at,
  pr_to_merge_sec,
  merge_to_learning_sec,
  pr_to_learning_sec
from lifecycle
order by proposal_id desc
limit 100;

-- averages
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
    cast((julianday(merged_at) - julianday(pr_created_at)) * 86400 as integer) as pr_to_merge_sec,
    cast((julianday(learning_at) - julianday(merged_at)) * 86400 as integer) as merge_to_learning_sec,
    cast((julianday(learning_at) - julianday(pr_created_at)) * 86400 as integer) as pr_to_learning_sec
  from ev
)
select
  round(avg(pr_to_merge_sec),1) as avg_pr_to_merge_sec,
  round(avg(merge_to_learning_sec),1) as avg_merge_to_learning_sec,
  round(avg(pr_to_learning_sec),1) as avg_pr_to_learning_sec
from lifecycle
where pr_to_merge_sec is not null
   or merge_to_learning_sec is not null
   or pr_to_learning_sec is not null;

-- missing lifecycle counts
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
)
select
  sum(case when pr_created_at is not null and merged_at is null then 1 else 0 end) as missing_merge_after_pr,
  sum(case when merged_at is not null and learning_at is null then 1 else 0 end) as missing_learning_after_merge,
  sum(case when pr_created_at is not null and learning_at is null then 1 else 0 end) as missing_learning_after_pr
from ev;

-- recent incomplete lifecycle
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
)
select
  proposal_id,
  pr_created_at,
  merged_at,
  learning_at
from ev
where (pr_created_at is not null and merged_at is null)
   or (merged_at is not null and learning_at is null)
order by proposal_id desc
limit 100;
