# Telegram OS 実装計画

## 目的
TelegramをOpenClaw全体の会話型OSにする。
ターミナル操作なしで、自然文のやり取りだけで以下を進められる状態を目指す。

- 商品分析
- LP制作
- 画像構成案作成
- 動画台本作成
- コピー改善
- 実装依頼
- バグ修正
- テスト
- PR作成
- 結果返却

## 理想状態
ユーザーはTelegramで自然文を送るだけにする。

例:
- educate Bを分析して勝ち軸を3つ出して
- 1案目でLPを作って
- 画像も整えて
- この表現を弱めて
- この実装を進めて
- 進捗だけ報告して

OpenClaw側は以下を自動で行う。
1. 指示分類
2. 文脈理解
3. タスク分解
4. 実行
5. 自己評価
6. 改善
7. 返答
8. 状態保存

## 実装方針
表は会話、裏は厳密にする。

- 表:
  - 自然文のみ
  - コマンド暗記不要
  - 次アクションがすぐ選べる返答
- 裏:
  - 案件ID管理
  - 状態遷移管理
  - 実行ログ管理
  - 成果物管理
  - 続き指示対応

## 対象領域
### 制作
- 商品分析
- LP生成
- バナー構成
- 画像構成案
- 動画台本
- SNS文
- 商品説明文

### 開発
- 要件整理
- 既存コード確認
- 実装
- テスト
- PR
- 反映候補整理

## 必須要件
1. Telegram自然文だけで開始できる
2. 前の続きが通る
3. 分析から次工程へ自動接続できる
4. 制作と開発を同じ会話基盤で扱う
5. 返答は常に次アクション可能にする
6. ターミナル常用を前提にしない
7. 作り直し最小のため、状態と成果物を必ず保存する

## 内部フロー
1. ingest
2. classify
3. resolve context
4. decompose
5. route worker
6. review
7. improve
8. format reply
9. persist state

## 必要コンポーネント
- conversation_intent_router_v1
- conversation_context_resolver_v1
- task_decomposer_v1
- creative_orchestrator_v1
- dev_orchestrator_v1
- review_loop_v1
- telegram_reply_formatter_v1

## Kaikun役割
### Kaikun02
- COO/会話窓口
- 依頼理解
- 進捗返答
- 次アクション提示
- 会話継続制御

### Kaikun04
- CTO/実行責任
- 制作と開発の実処理指揮
- worker選定
- review/improve進行
- 実行完了判定

## DBで持つべき情報
- conversation_jobs
  - id
  - source_chat_id
  - source_message_id
  - domain
  - request_text
  - target_object
  - current_phase
  - status
  - assigned_ai
  - parent_job_id
  - created_at
  - updated_at

- conversation_job_steps
  - id
  - job_id
  - step_type
  - step_order
  - status
  - input_json
  - output_json
  - created_at
  - updated_at

- conversation_artifacts
  - id
  - job_id
  - artifact_type
  - artifact_title
  - artifact_body
  - artifact_path
  - version
  - created_at

## 初期フェーズ
### Phase 1
制作・分析系をTelegram完結
- 商品分析
- 勝ち軸抽出
- LP3案生成
- 自己評価
- 改善提案

### Phase 2
開発系をTelegram完結
- 要件整理
- 実装
- テスト
- PR要約
- 完了返答

### Phase 3
反映系をTelegram完結
- 反映候補整理
- 実行可否補助
- 完了報告

## 最初の実案件
educate B を対象に以下をテンプレ化する。
1. 商品ページ解析
2. 成分抽出
3. 勝ち軸3案
4. LP3案
5. 自己評価
6. 改善
7. Telegram返答整形

## 完了条件
- Telegramで自然文を送ると制作依頼が最後まで流れる
- Telegramで自然文を送ると開発依頼が最後まで流れる
- 続き指示が通る
- 返答に次アクション候補が出る
- 文脈と成果物がDBに残る
