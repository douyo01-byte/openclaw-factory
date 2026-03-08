# OpenClaw Handover

## 前提

- この文書は最新の正規引き継ぎ
- 古いチャットよりこの文書を優先
- 実ファイル・実DB・実ログ・実プロセスを優先
- 設計変更ではなく現状確認を先に行う

## 引き継ぎテンプレ

【今回やったこと】
- docs/11_OPERATIONS.md, docs/17_EFFICIENCY_RULES.md, docs/20_DAILY_OPERATION.md を整備
- docs/README.md を作成
- docs/00_INDEX.md を作成
- docs/04_ARCHITECTURE.md を更新
- scripts/fix_docs_spacing.py を作成し運用へ組み込み
- daily operation の試走を実施
- LaunchAgent 稼働状態と DB 実数を確認
- docs 一式を Git 管理へ追加して push 済み

【進んだこと】
- 母艦運用ルールが docs 化された
- スマホ更新時の spacing 修正フローが確立した
- daily operation の試走が通った
- 主要 LaunchAgent が running であることを確認した
- docs の入口とナビゲーションが整った
- architecture docs を現行方針に整理した

【まだ未完のこと】
- docs 内の重複追記整理
- docs の実測値反映の継続
- 3核以外の md の最終見直し
- docs 間の役割分担の微調整

【現在の本当の状態】
- supervisor / dev_command_executor / dev_pr_watcher / tg_poll_loop / self_healing は running
- dev_proposals は 808 を確認
- proposal_state は refined=11 / merged=2 / executed=1 / pr_created=1
- ceo_hub_events は merged=50 / learning_result=4 / pr_created=3
- daily operation 試走は通過済み
- docs は Git 管理下へ追加済み
- docs/README.md と docs/00_INDEX.md を新設済み
- docs/04_ARCHITECTURE.md を現行版へ更新済み

【確認できたファイル / DB / プロセス】
- docs/04_ARCHITECTURE.md
- docs/06_CURRENT_STATE.md
- docs/08_HANDOVER.md
- docs/11_OPERATIONS.md
- docs/17_EFFICIENCY_RULES.md
- docs/20_DAILY_OPERATION.md
- docs/README.md
- docs/00_INDEX.md
- scripts/fix_docs_spacing.py
- launchctl print
- sqlite3 data/openclaw.db

【危険点】
- docs に一部重複追記あり
- スマホ経由更新では spacing 崩れ再発可能性あり
- docs の概算値と実測値がずれるので定期更新が必要
- 旧 docs と新 docs の役割が一部近接している

【次チャットで最初に打つコマンド】
cd ~/AI/openclaw-factory || exit 1

【次チャットでやること】
1. docs の重複整理
2. docs へ実測値反映
3. 3核以外の md 最終見直し

【母艦チャットに反映すべきこと】
- daily operation 運用が通った
- spacing 修正スクリプト運用を導入
- 主要 LaunchAgent は running
- DB 実測値は docs 概算より現在低い
- docs 一式は Git 管理下に入った


## 2026-03-09 handover: proposal loop stabilized

### 今回の到達点
- proposal 系の `approved -> refined -> pr_created -> merged` を連続確認
- 927〜942 まで merged 到達を確認
- `proposal_state` の中間残件は解消済み

### 修正した主対象
- `bots/spec_refiner_v2.py`
- `bots/spec_notify_v1.py`
- `bots/dev_executor_v1.py`
- `bots/dev_pr_automerge_v1.py`
- `bots/dev_pr_watcher_v1.py`
- `bots/auto_pr_v1.py`
- `scripts/run_dev_pr_automerge_v1.sh`

### 重要変更
- refiner が approved proposal を拾えるよう修正
- notify の通知経路修正
- automerge の env / runner 修正
- generator に sanitize を追加し、fenced code と conflict marker による CI failure を防止
- watcher が `proposal_state.stage` を merged/closed に同期するよう修正
- 壊れた tracked `autogen.py` は main から削除済み（hotfix PR #885）

### 現在の見方
- proposal loop は通ったと判断してよい
- 次フェーズは proposal 疎通確認の反復ではなく、
  - docs 整理
  - 運用ルール反映
  - 未整理変更の切り分け
  - mother report 更新
 へ移る

### 注意
- executor は 600 秒間隔制御あり
- sqlite readonly 参照で lock が出る場合あり
- ただし proposal loop の成立自体は確認済み

