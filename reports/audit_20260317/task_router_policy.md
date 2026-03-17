# Task Router Policy (2026-03-17)

## PURPOSE
- task_router_v1 は inbox_commands を Kaikun02 / Kaikun04 に正しく振り分ける
- Kaikun02 は quick reply / COO補助 / 運用即答
- Kaikun04 は THINK / 深い整理 / 長文要約 / 重い分析

## ROUTING PRINCIPLE
- 即答・運用確認・現状確認・ランキング・runtime分類・ボトルネック・監視ポイント
  -> kaikun02
- 長文整理・設計比較・構造化・重い分析・考察・THINK付き依頼
  -> kaikun04

## KAIKUN02 CLASS
- progress / status / 現状
- next actions
- weak points
- ai employee ranking
- runtime classification
- flow bottleneck
- top watchpoints

## KAIKUN04 CLASS
- THINK
- deep analysis
- long summary
- design整理
- 比較検討
- 構造化タスク
- 母艦向けの重い整理

## RULE
- 迷ったら quick/short は kaikun02
- 重い整理・長文化・設計判断は kaikun04
- quick route を追加したら
  - kaikun02_router_worker_v1.py
  - bots/kaikun02_router_cleanup_v1.py
  - scripts/run_final_sanity_v1.sh
  - reports/audit_20260317/kaikun02_route_policy.md
  を同時更新する

## JUDGMENT
- current router policy prefers operational speed on kaikun02
- current router policy reserves deep reasoning for kaikun04
