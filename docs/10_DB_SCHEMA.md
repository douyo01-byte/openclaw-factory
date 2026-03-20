# DB SCHEMA

## source of truth
- ~/AI/openclaw-factory/data/openclaw.db

## core tables
- dev_proposals
- proposal_state
- ceo_hub_events
- ops_watcher_events
- decisions

## notes
- runtime count は MD に固定記載しない
- 状態確認は DB へ直接問い合わせる
- ceo_hub_events の本文列は title / body
- ops_watcher_events の主要列は kind / body
