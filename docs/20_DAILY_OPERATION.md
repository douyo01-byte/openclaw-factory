# OpenClaw Daily Operation

## 朝の確認

1. supervisor確認
2. tg_poll_loop確認
3. dev_command_executor確認
4. dev_pr_watcher確認
5. self_healing確認
6. proposal件数と直近の流れ確認
7. CEOダッシュボード確認
8. 異常ログ確認

## 朝の基本コマンド

cd ~/AI/openclaw-factory-daemon || exit 1

uid=$(id -u)
for s in \
  jp.openclaw.supervisor \
  jp.openclaw.dev_command_executor_v1 \
  jp.openclaw.dev_pr_watcher_v1 \
  jp.openclaw.tg_poll_loop \
  jp.openclaw.self_healing_v2 \
  jp.openclaw.spec_refiner_v2
do
  echo "===== $s ====="
  launchctl print "gui/$uid/$s" | egrep 'state =|pid =|last exit code|stdout path|stderr path' || true
done

cd ~/AI/openclaw-factory || exit 1
sqlite3 data/openclaw.db "select count(*) as dev_proposals from dev_proposals;"
sqlite3 data/openclaw.db "select stage,count(*) from proposal_state group by stage order by count(*) desc;"
sqlite3 data/openclaw.db "select event_type,count(*) from ceo_hub_events group by event_type order by count(*) desc;"

## 作業前

- 今日は factory を触るか daemon を触るか決める
- 触る範囲と触らない範囲を決める
- 実在確認してから作業する

## 作業後

必ず以下を行う:
1. docs/08_HANDOVER.md 形式で結果整理
2. 必要なら docs/06_CURRENT_STATE.md 更新
3. スマホ更新なら python scripts/fix_docs_spacing.py 実行
4. 母艦に反映すべき内容を抜き出す

## 夜の確認

1. todayの変更点確認
2. 壊したものがないか確認
3. 次チャット最初のコマンド確定
4. handover更新
5. 母艦へ戻す内容を確定

## 週1メンテ

- archive候補確認
- LaunchAgentの現役/残骸確認
- broken/bakの棚卸し
- docsの古い情報整理
- proposal供給量の評価
- learning評価軸の見直し
