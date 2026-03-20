# MAINLINE IMPLEMENTATION GATE

## purpose
Kaikun04 / 人間 / 今後の実装判断はこのファイルを mainline 実装の入口にする。

## single source
- DB: ~/AI/openclaw-factory/data/openclaw.db
- runtime truth > docs

## allowed mainline targets
- jp.openclaw.ops_brain_agent_v1
- jp.openclaw.dev_pr_watcher_v1
- jp.openclaw.brain_supply_v1
- jp.openclaw.proposal_cluster_v1
- jp.openclaw.pattern_extractor_v1
- jp.openclaw.supply_bias_updater_v1
- jp.openclaw.ingest_private_replies_kaikun02
- jp.openclaw.ingest_private_replies_kaikun04

## implementation rule
1. まず docs/01_SINGLE_SOURCE_OF_TRUTH.md を確認
2. 次に docs/02_ROLE_REGISTRY.md で役割を確認
3. 次に docs/03_KAIKUN04_RUNTIME_RULE.md を確認
4. 次に docs/04_KAIKUN04_STARTER.md を確認
5. 既存ファイルへ統合できるかを先に確認
6. mainline以外には原則追加しない

## forbidden
- 新規bot作成
- 同一役割の複数bot
- selector / normalizer / bridge の再増殖
- legacy router系の復活
- docsだけ更新して runtime未確認のまま判断

## next objective
- Kaikun04 の判断を mainline active と docs/05 起点に統一
- business worker は mainline直結の形でのみ再開
