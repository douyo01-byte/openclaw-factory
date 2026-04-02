# OpenClaw Master Plan

## 目的
OpenClawは「AI会社OS」であり、
Telegram上でAI社員が判断・実行・学習・改善を行う構造を作る。

---

## 現在の最重要方針（更新）

1. 開発部門強化 → 継続
2. OpenClaw本体強化 → 最優先
3. 「ツール開発」ではなく「思考エンジン強化」に集中
4. OSSは手足として吸収する（自作しない）
5. Kaikunの判断精度と学習ループを価値の中核とする
6. DB（learning_results / patterns）を競争優位とする
7. Telegram OSをUIの中心に固定
8. API依存を最小化（ローカル優先）
9. 外部課金・契約は人間承認必須
10. docs / DB / runtime の一致を絶対基準とする

---

## OpenClawの正しい構造（進化版）

入力（Telegram / 外部）
↓
Kaikun判断（何をやるか決定）
↓
実行（OSS / ローカル / API）
↓
成果（artifact / DB）
↓
学習（learning_results / patterns）
↓
次の判断へ反映

---

## 開発方針（重要）

❌ ツールを作る
⭕ 判断と成長を作る

---

## 自作領域（コア）

- Kaikun判断ロジック
- 学習DB
- 改善ループ
- タスク配分
- 成果評価

---

## 外部活用領域（手足）

- EXEC基盤
- エージェント実行
- ワークフロー
- API接続
- モデル

---

## 現在の重点

1. 構造の棚卸し（bot / DB / LaunchAgent）
2. OSS吸収設計
3. ローカル / API / OSS の責務分離
4. 学習ループの強化
5. Kaikunの意思決定精度向上

---

## 理想状態

朝起きたらOpenClawが進化している状態

