# OpenClaw next runtime resume plan

## 固定できた状態
- minimal runtime only
- active:
  - jp.openclaw.open_pr_guard_v1
  - jp.openclaw.dev_pr_watcher_v1
- unique open PR count = 25
- duplicate open pr_url = 0

## open PR by source
- mothership: 14
- strategy_engine: 6
- innovation_engine: 3
- cto: 2

## 再開順
1. proposal_promoter_v1
2. spec_refiner_v2
3. spec_decomposer_v1
4. dev_pr_creator_v1
5. innovation_engine_v1
6. strategy_engine_v1
7. proposal_builder_loop_v1

## 再開条件
- unique open PR count <= 15
- duplicate open pr_url = 0
- closed / merged と pr_status の不整合が増えていない

## 毎回最初に確認するSQL
select count(distinct pr_url)
from dev_proposals
where coalesce(pr_status,'')='open'
  and coalesce(pr_url,'')<>'';

select
  coalesce(source_ai,''), count(distinct pr_url)
from dev_proposals
where coalesce(pr_status,'')='open'
  and coalesce(pr_url,'')<>''
group by 1
order by 2 desc;

select
  pr_url,
  count(*) as n,
  group_concat(id) as ids
from dev_proposals
where coalesce(pr_status,'')='open'
  and coalesce(pr_url,'')<>''
group by pr_url
having count(*) > 1
order by n desc, pr_url asc;
