# KAIKUN04 RUNTIME RULE

## Purpose
Kaikun04は必ず同じ入口から判断する。
思いつき実装を禁止し、既存統合を最優先にする。

## Mandatory Flow
1. docs/01_SINGLE_SOURCE_OF_TRUTH.md を確認
2. docs/02_ROLE_REGISTRY.md を確認
3. 対象が Mainline / Meta / Business のどれかを決定
4. 既存botへ統合可能か判定
5. mode追加で吸収可能か判定
6. 重複なら新規禁止
7. それでも不可なら新規作成を検討

## Hard Gates
以下を満たさない提案・実装は却下する

- SINGLE SOURCE未確認
- ROLE未確認
- 重複判定なし
- 統合先未確認
- 新規bot前提

## Duplicate Check
以下のいずれかに該当したら統合対象

- 同じ入力
- 同じ処理
- 同じ目的
- 同じタイミングで動く
- 既存botのmode追加で吸収可能

## Reject
以下は原則却下

- bridge追加
- selector追加
- normalizer追加
- watcher追加
- 似た役割のbot追加
- runtime truthをMDで決める行為

## Output Format
Kaikun04の判断出力は必ず以下順

1. Classification
2. Existing Target
3. Duplicate Risk
4. Integration Decision
5. Action

## Final Rule
新規作成より先に、既存統合案を必ず出す。

## Fixed Private Reply Route
private reply は以下のみを本流とする
1. ingest_private_replies_kaikun04
2. private_reply_to_inbox_v1
3. secretary_llm_v1

以下は本流扱いしない
- ingest_private_replies_kaikun02
- ingest_private_replies_v1
- ingest_private_chat_v1
- router_reply_finisher_v1

## Current Ops Watcher Targets
### required
- jp.openclaw.ops_brain_agent_v1
- jp.openclaw.private_reply_to_inbox_v1

### observe
- jp.openclaw.dev_pr_automerge_v1
- jp.openclaw.db_integrity_watchdog_v1
- jp.openclaw.kaikun02_coo_controller_v1
- jp.openclaw.dev_pr_watcher_v1
- jp.openclaw.ingest_private_replies_kaikun04
- jp.openclaw.secretary_llm_v1
