# KAIKUN02 RUNTIME MEMO

## 事実
- 実働最小系は open_pr_guard_v1 / dev_pr_watcher_v1 / dev_pr_creator_v1
- open PR queue は現在 15
- duplicate open pr_url は 0
- dev_proposals が中核DB
- proposal_state は pending_question 列を期待する運用
- source_ai 空欄の旧履歴が残っている
- botファイル大量存在 = 本番稼働 ではない

## 今の本番判断
### 本番に近い
- open_pr_guard_v1
- dev_pr_watcher_v1
- dev_pr_creator_v1
- proposal_promoter_v1
- spec_refiner_v2
- spec_decomposer_v1

### 要監査
- innovation_engine_v1
- strategy_engine_v1
- proposal_builder_loop_v1
- reasoning_engine_v1
- proposal_throttle_engine_v1
- learning_result_writer_v1
- pattern_extractor_v1
- supply_bias_updater_v1

## producer再開条件
- unique open PR count <= 15
- duplicate open pr_url = 0
- closed / merged と pr_status の不整合増加なし
- creator / watcher / guard の3点が安定

## 毎回最初に見るSQL
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

select count(*)
from (
  select pr_url
  from dev_proposals
  where coalesce(pr_status,'')='open'
    and coalesce(pr_url,'')<>''
  group by pr_url
  having count(*) > 1
);
