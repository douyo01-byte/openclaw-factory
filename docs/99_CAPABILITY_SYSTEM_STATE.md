# CAPABILITY SYSTEM STATE (Kaikun04)

## 概要
OpenClaw は capability_registry を中心に
全ての実行能力を統合している

---

## SINGLE SOURCE

capability_registry が唯一の能力台帳

扱う能力タイプ：

- repo_exec
- auto_skill
- self_evolution

---

## 実行フロー

Kaikun04

THINK
↓
capability_registry 検索
↓
最適 capability 選択
↓
EXEC 生成
↓
ops_exec 実行

---

## 優先順位ロジック

self_evolution の場合：

1. new（最新）
2. applied
3. failed は選ばない

---

## 実証ログ

- self_evolution:13 → failed (pattern_not_found)
- self_evolution:12 → applied

結果：

Kaikun04 は 13 を選ばず 12 を選択

---

## 直近ログ

- router_task_id=1953
  decision=self_evolution_reuse
  capability_key=self_evolution:12

- router_task_id=1952
  decision=self_evolution_reuse
  capability_key=self_evolution:12

---

## 意味

OpenClaw は以下を獲得：

- 能力の統一管理
- 実行履歴ベースの選択
- 失敗回避
- 自己改善ループ

---

## 状態

- capability routing: 正常
- self_evolution routing: 正常
- failed avoidance: 動作確認済み

---

## 次の進化

- success率ベースの重み付け
- task_text semantic matching
- capability 自動生成の強化

