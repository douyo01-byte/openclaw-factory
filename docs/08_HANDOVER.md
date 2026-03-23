# OpenClaw Handover

## 前提
- 実ファイル・実DB・実ログ・実process を docs より優先する
- docs は現状把握の補助、最終判断は runtime 実態で行う

## 最初に見るもの
1. docs/06_CURRENT_STATE.md
2. docs/12_RUNTIME_CLASSIFICATION.md
3. ../openclaw-factory/data/openclaw.db の live 状態
4. ../openclaw-factory-daemon の launchctl 実態
5. ops_watcher_events / ceo_hub_events の最新行

## 現在の本当の状態
- source of truth DB: /Users/doyopc/AI/openclaw-factory/data/openclaw.db
- open_pr: 0
- watcher required:
  - jp.openclaw.ops_brain_agent_v1
  - jp.openclaw.private_reply_to_inbox_v1
  - jp.openclaw.secretary_llm_v1
- watcher observe:
  - jp.openclaw.dev_pr_automerge_v1
  - jp.openclaw.db_integrity_watchdog_v1
  - jp.openclaw.kaikun02_coo_controller_v1
  - jp.openclaw.dev_pr_watcher_v1
  - jp.openclaw.ingest_private_replies_kaikun04
- proposal -> PR -> merged -> executor_audit の本線は稼働中

## 次チャットで最初に打つコマンド
cd ~/AI/openclaw-factory-daemon || exit 1

## 次に確認する項目
1. openclaw.db の件数
2. ceo_hub_events 最新行
3. ops_watcher_events 最新行
4. watcher の required / observe 対象
5. legacy launchagent の棚卸し

## 現在の本流
### private reply
- ingest_private_replies_kaikun04
- private_reply_to_inbox_v1
- secretary_llm_v1
- inbox_commands.secretary_done

### watcher
- required:
  - jp.openclaw.ops_brain_agent_v1
  - jp.openclaw.private_reply_to_inbox_v1
  - jp.openclaw.secretary_llm_v1
- observe:
  - jp.openclaw.dev_pr_automerge_v1
  - jp.openclaw.db_integrity_watchdog_v1
  - jp.openclaw.kaikun02_coo_controller_v1
  - jp.openclaw.dev_pr_watcher_v1
  - jp.openclaw.ingest_private_replies_kaikun04

## Private Reply Single Source

    Telegram(private)
    -> tg_private_chat_log
    -> private_reply_to_inbox_v1
    -> inbox_commands
    -> secretary_llm_v1
    -> secretary_done

Legacy router runtimes were archived into archive/router_legacy_20260322 and are not part of the active private reply path.

## Private Reply Mainline
- Telegram(private)
- tg_private_chat_log
- ingest_private_replies_kaikun04
- private_reply_to_inbox_v1
- inbox_commands
- secretary_llm_v1
- secretary_done

## Router Structure
- Kaikun02 = FAST
- Kaikun04 = THINK

## Entry Gate / Input Guard
- blank / 1文字 / URL単体 は除外
- duplicate 抑止
- short = fast
- long / [THINK] / 分析要求 = think

## Watcher Definition
### required
- jp.openclaw.private_reply_to_inbox_v1
- jp.openclaw.secretary_llm_v1

### observe
- jp.openclaw.ingest_private_replies_kaikun04

## ACTIVE本流
### dev pipeline
- dev_proposals
- spec_refiner_v2
- dev_executor_v1
- dev_pr_watcher_v1
- dev_pr_automerge_v1

### router
- Kaikun02 = FAST
- Kaikun04 = THINK

### private reply
- Telegram(private)
- tg_private_chat_log
- ingest_private_replies_kaikun04
- private_reply_to_inbox_v1
- inbox_commands
- secretary_llm_v1
- secretary_done

### watcher
#### required
- jp.openclaw.private_reply_to_inbox_v1
- jp.openclaw.secretary_llm_v1

#### observe
- jp.openclaw.ingest_private_replies_kaikun04

