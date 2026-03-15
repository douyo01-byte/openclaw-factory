# OpenClaw next runtime resume plan

## 現在の安全状態
- producer群は停止
- activeは open_pr_guard_v1 / dev_pr_watcher_v1
- unique open PR count = 25
- open_pr_guard_v1 は unique pr_url ベースで上限制御済み

## 次の再開順
1. proposal_promoter_v1
2. spec_refiner_v2
3. spec_decomposer_v1
4. dev_pr_creator_v1
5. innovation_engine_v1 / strategy_engine_v1 / proposal_builder_loop_v1 は最後

## 再開条件
- unique open PR count <= 15 になってから producer再開
- duplicate pr_url の再発がない
- closed / merged と pr_status の不整合が増えていない

## 次回まず確認するSQL
select count(distinct pr_url)
from dev_proposals
where coalesce(pr_status,'')='open'
  and coalesce(pr_url,'')<>'';

select coalesce(source_ai,''), count(distinct pr_url)
from dev_proposals
where coalesce(pr_status,'')='open'
  and coalesce(pr_url,'')<>''
group by 1
order by 2 desc;
