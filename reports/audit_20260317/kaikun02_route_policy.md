# Kaikun02 Route Policy (2026-03-17)

## QUICK_REPLY
- dashboard
- next_tasks
- weak_points
- ai_employee_ranking
- runtime_classification
- flow_bottleneck
- top_watchpoints

## RELAY
- 上記以外は relay
- relay は router_tasks.status=new -> started で Telegram へ送信
- private reply が返れば finisher が done 化

## CLEANUP
- quick-route相当の質問なのに過去 relay 済みで残っている started/new は cleanup 対象
- cleanup 条件:
  - target_bot=kaikun02
  - status in (new, started)
  - updated_at / created_at が 30分以上前
  - task_text が quick-route系キーワードに一致

## OPERATIONS
- 母艦 / Kaikun02 は runtime説明より先に quick route 一覧を前提として扱う
- quick route に追加したら run_final_sanity_v1.sh の grep も必ず更新
