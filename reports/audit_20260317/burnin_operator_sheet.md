# Burn-in Operator Sheet (2026-03-17)

## Canonical DB
- /Users/doyopc/AI/openclaw-factory/data/openclaw.db

## Watch items
- open_pr_count
- blank_source_ai
- merged_without_result_type
- stage_divergence_count
- router_tasks new/started growth
- dev_proposals open PR growth
- DB lock symptoms

## Known non-issue
- router_tasks timeout=1 is old timeout test row id=62 from 2026-03-14

## One-shot checks

1. Final sanity
   cd ~/AI/openclaw-factory-daemon || exit 1
   ./scripts/run_final_sanity_v1.sh

2. Router counts
   sqlite3 -cmd ".headers on" -cmd ".mode column" /Users/doyopc/AI/openclaw-factory/data/openclaw.db "
   select
     coalesce(target_bot,'') as target_bot,
     coalesce(status,'') as status,
     count(*) as cnt
   from router_tasks
   group by 1,2
   order by 1,2;
   "

3. Open PR count
   sqlite3 -cmd ".headers on" -cmd ".mode column" /Users/doyopc/AI/openclaw-factory/data/openclaw.db "
   select count(*) as open_pr
   from dev_proposals
   where coalesce(pr_status,'')='open'
     and coalesce(pr_url,'')<>'';
   "

## Operator policy
- burn-in中は dormant bots を復帰しない
- current ACTIVE mainline のみ監視・保守
- timeout=1 は row id=62 の旧テスト履歴として扱う
