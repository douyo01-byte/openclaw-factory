select
  source,
  count(*) as proposals,
  sum(case when status='approved' then 1 else 0 end) as approveds,
  sum(case when status='merged' then 1 else 0 end) as mergeds
from dev_proposals
where source is not null and trim(source) <> ''
group by source
order by mergeds desc, proposals desc, source asc;
