# MAINLINE IMPLEMENTATION GATE
## purpose
Kaikun04 / 人 間 / 今 後 の 実 装 判 断 は こ の フ ァ イ ル を mainline 実 装 の 入 口 に す る 。

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
1. ま ず docs/01_SINGLE_SOURCE_OF_TRUTH.md を 確 認
2. 次 に docs/02_ROLE_REGISTRY.md で 役 割 を 確 認
3. 次 に docs/03_KAIKUN04_RUNTIME_RULE.md を 確 認
4. 次 に docs/06_META_KEEP_HOLD.md を 確 認
5. 次 に docs/07_BUSINESS_KEEP_HOLD.md を 確 認
6. 既 存 フ ァ イ ル へ 統 合 で き る か を 先 に 確 認
7. mainline以 外 に は 原 則 追 加 し な い

## forbidden
- 新 規 bot作 成
- 同 一 役 割 の 複 数 bot
- selector / normalizer / bridge の 再 増 殖
- legacy router系 の 復 活
- docsだ け 更 新 し て runtime未 確 認 の ま ま 判 断

## next objective
- Kaikun04 の 判 断 を mainline active と docs/05 起 点 に 統 一
- business worker は mainline直 結 の 形 で の み 再 開
