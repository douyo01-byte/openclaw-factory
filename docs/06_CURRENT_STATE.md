# OpenClaw Current State

## 現在地

開発AI:
Lv5.4〜Lv5.5

理由:
- dev_command_executor_v1 実運用
- dev_pr_watcher_v1 実運用
- tg_poll_loop 実運用
- self_healing_v2 実運用
- spec_refiner_v2 / spec_reply_v1 / spec_notify_v1 実運用
- dev_proposal_notify_daemon_v1 実運用
- ai_employee_manager_v1 実運用
- 主幹自律ループが成立
- daily operation 試走が通過
- docs 運用基盤を整備
- docs/README.md / docs/00_INDEX.md / docs/04_ARCHITECTURE.md を整備
- dev_proposals は現在 808 を確認

ただし未完成寄り:
- proposal供給量
- learning評価軸
- 完全自律安定化
- self-healing の精度向上
- docs 重複整理
- docs 実測値の定期反映

事業AI:
Lv4後半〜Lv5手前

理由:
- market / business / revenue 系 brain は存在
- SekawakuClaw 系運用あり
- 事業側 BOT 構造はある

ただし:
- 供給量が弱い
- 母体強化向け案件生成に寄せている段階
- 事業拡張は後段

AI社員会社構想:
- 役割設計は完成
- UI人格も整理済み
- 運用基盤は未完成

## 総合評価

- 開発部門はかなり進んでいる
- 事業部門は構造あり・供給不足
- AI社員は設計済み・基盤構築中

思想としては Lv6発想まで到達しているが、実装成熟度はまだ Lv6未満。

## 現在の最優先課題

1. docs の重複整理
2. docs への実測値反映
3. proposal供給量
4. learning評価軸
5. CEOダッシュボード精度

## 現在確認済みの実測状態

主要 LaunchAgent / 常駐系:
- supervisor: running
- dev_command_executor: running
- dev_pr_watcher: running
- tg_poll_loop: running
- self_healing: running

DB 実測:
- dev_proposals: 808
- proposal_state: refined=11 / merged=2 / executed=1 / pr_created=1
- ceo_hub_events: merged=50 / learning_result=4 / pr_created=3


## 6分割時点から解消済み

- executor停止: dev_command_executor 起動ミス修正済み
- DB_PATH分裂: factory / daemon 不一致修正済み
- PR詰まり: conflict PR 整理済み
- proposal diversity 実装済み
- OPS BOT未接続: Kaikun03接続済み


## 2026-03-09 Proposal Loop疎通確認

### 確認済み
- spec_refiner_v2 の pick 条件修正により、approved proposal が refined まで進行することを確認
- spec_notify 系の通知経路修正により、refined proposal の通知が正常化
- dev_pr_automerge_v1 の起動経路と env 読み込みを修正
- auto_pr_v1 に生成コードサニタイズを追加
  - code fence 除去
  - conflict marker 除去
- main に残っていた壊れた `autogen.py` を hotfix PR #885 で削除
- dev_pr_watcher_v1 を修正し、`dev_proposals` の status/dev_stage だけでなく `proposal_state.stage` も merged/closed に同期するよう更新

### 実通過
- proposal 927〜942 で以下の一連疎通を確認
  - approved
  - refined
  - pr_created
  - merged

### 最終確認
- PR #900 merged
- `dev_proposals.id=942` は `merged`
- `proposal_state` の `refined / pr_created / executed` 残件は 0 まで解消を確認

### 現在の評価
- proposal pipeline は現行構成で end-to-end 疎通確認済み
- 実運用上は loop として成立
- executor には `MIN_PR_INTERVAL_SEC=600` の間隔制御あり
- sqlite 読み取り時に一時的な `database is locked` は出るが、proposal loop 自体は成立

