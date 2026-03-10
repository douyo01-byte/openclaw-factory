select 'pr_created_without_merged' as metric, count(*) as cnt
from (
  select proposal_id
  from ceo_hub_events
  where event_type in ('pr_created','proposal_created')
  group by proposal_id
) a
left join (
  select proposal_id
  from ceo_hub_events
  where event_type in ('merged','pr_merged','merge')
  group by proposal_id
) b
on a.proposal_id = b.proposal_id
where a.proposal_id is not null
  and b.proposal_id is null;

select 'merged_without_learning_result' as metric, count(*) as cnt
from (
  select proposal_id
  from ceo_hub_events
  where event_type in ('merged','pr_merged','merge')
  group by proposal_id
) a
left join (
  select proposal_id
  from ceo_hub_events
  where event_type in ('learning_result','learning','learned')
  group by proposal_id
) b
on a.proposal_id = b.proposal_id
where a.proposal_id is not null
  and b.proposal_id is null;
