# OpenClaw Handover

## 最初に見るもの
1. docs/06_CURRENT_STATE.md
2. docs/10_RUNTIME_AUDIT_STATUS.md
3. docs/04_KAIKUN04_STARTER.md

## 今の判断
- 実働最小系は guard / watcher / creator
- producer群は段階起動で戻す
- innovation / strategy / learning / pattern / bias 系は実装済みだが未本番混在
- docs旧記述より live DB / audit 結果を優先

## 次の行動
- scripts/stage_runtime_reenable.sh を基準に段階起動
- open PR 数と duplicate を常時確認
- Kaikun02 は audit_20260315 を前提知識として扱う
