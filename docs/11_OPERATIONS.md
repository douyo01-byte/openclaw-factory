# OpenClaw Operations

## 固定確認手順
cd ~/AI/openclaw-factory-daemon || exit 1
python3 scripts/check_watcher_health_24h.py
launchctl list | grep openclaw || true
ls -l data/openclaw.db

## 正常条件
- watcher 24h:
  - restarted=0
  - escalations=0
  - notifications=0
  - proposals=0
- required 3 targets running
- daemon DB が factory DB への symlink になっている

## required targets
- `jp.openclaw.ops_brain_agent_v1`
- `jp.openclaw.private_reply_to_inbox_v1`
- `jp.openclaw.secretary_llm_v1`

## DB確認
cd ~/AI/openclaw-factory-daemon || exit 1
ls -l data/openclaw.db
readlink data/openclaw.db || true
lsof | grep openclaw.db | wc -l

## runtime確認
u=$(id -u)
for t in \
jp.openclaw.ops_brain_agent_v1 \
jp.openclaw.private_reply_to_inbox_v1 \
jp.openclaw.secretary_llm_v1
do
  echo "--- $t ---"
  launchctl print "gui/$u/$t" | egrep 'state =|pid =|last exit code =|path =|program ='
done

## private reply本流
- `Telegram -> tg_private_chat_log -> inbox_commands -> secretary_done`

## 運用ルール
- 推測で直さない
- docs / DB / runtime の不一致だけを修正する
- required / observe のズレを増やさない
- 新規機能追加はしない
