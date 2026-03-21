# OpenClaw SINGLE SOURCE

## DB
~/AI/openclaw-factory/data/openclaw.db

## Runtime Truth
- 状態は必ずDBから取得する
- MDは状態を持たない

## System Structure
- Mainline（開発本線）
- Meta Control（監視・制御）
- Business Worker（事業）

## Human Role
- 承認
- 外部コミュニケーションのみ

## Bot Creation Rule
- 新規作成は禁止
- 必ず以下を通す
  1. 既存botへ統合
  2. mode追加
  3. それでも無理なら新規

## Execution Rule（最重要）
すべての実装は以下を通過すること：

1. SINGLE SOURCE確認
2. 既存構造確認
3. 重複判定
4. 統合先決定
5. 実装

※この順序を飛ばした実装は禁止

## Absolute Rules
- 新規botは原則禁止
- 同一役割の複数botは禁止
- 既存機能の再実装は禁止
- 改善は必ず既存統合から検討

## Forbidden
- 思いつきで新bot作成
- 同一役割の複数bot
- runtime情報をMDに書く
- 既存構造を無視した改善

## Integration Decision
新規機能は必ず以下で判定：

1. 既存botに追加できるか？
2. modeで対応できるか？
3. それでも無理なら新規

→ 1か2で通るなら新規禁止

## Duplicate Detection
以下に該当したらNG：

- 同じ入力を扱う
- 同じ処理をする
- 同じ目的

→ 統合対象

## Reject Conditions
以下は即却下：

- 似た役割のbot追加
- bridge / selector / normalizer の追加
- watcherの増殖

## Input Classification
入力は以下に分類：

- 状態確認
- 改善提案
- 実装修正
- 事業追加
- 緊急対応

## Command Format
[目的] + [対象] + [制約]

例：
「重複削減 + selector系 + 新規bot禁止」

## Kaikun04 Flow
1. SINGLE SOURCE確認
2. 役割確認
3. 重複チェック
4. 統合先決定
5. 実装

## Current Focus（最大3つ）
1.
2.
3.

## Current Runtime Fixed Path
- private reply 本流:
  1. jp.openclaw.ingest_private_replies_kaikun04
  2. jp.openclaw.private_reply_to_inbox_v1
  3. jp.openclaw.secretary_llm_v1
- runtime truth は launchd / DB を優先
- docs は判断規則を持つが、状態そのものは持たない
