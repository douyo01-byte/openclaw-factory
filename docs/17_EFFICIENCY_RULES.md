# OpenClaw Efficiency Rules

1. まず確認
2. 次に判断
3. 最後に修正
4. 実在しないものを前提に話を進めない
5. 相談内容は
   - 今の状態
   - 何が欲しいか
   - 何を壊したくないか
   の3点で整理する
6. 1チャット1主題
7. 重くなったら引き継ぎを先に作る
8. 母艦チャットに現在地を戻す
9. 実装と思想を混ぜすぎない
10. まずは母艦強化を優先する

## スマホ運用ルール

- スマホからの長文貼り付け後は docs の空白崩れを疑う
- docs 更新後は python scripts/fix_docs_spacing.py を実行する
- 崩れ確認は sed -n '1,20p' docs/01_SYSTEM_PROMPT.md を使う

## docs更新ルール

作業チャット終了時は必ず以下を確認する。

更新対象:
- docs/06_CURRENT_STATE.md
- docs/08_HANDOVER.md

更新内容:

### docs/06_CURRENT_STATE.md
- OpenClawの現在状態
- 稼働中bot
- DB状態
- 重要構造

### docs/08_HANDOVER.md
- 今回やったこと
- 現在地
- 残タスク
- 次チャット最初のコマンド

長期方針変更時のみ更新:
- docs/01_SYSTEM_PROMPT.md
- docs/02_MASTER_PLAN.md
- docs/07_ROADMAP.md

## スマホ運用ルール

- スマホからの長文貼り付け後は docs の空白崩れを疑う
- docs更新後は python scripts/fix_docs_spacing.py を実行する
- 崩れ確認は sed -n '1,20p' docs/01_SYSTEM_PROMPT.md を使う
