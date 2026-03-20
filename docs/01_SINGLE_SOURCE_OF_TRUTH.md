# OpenClaw SINGLE SOURCE

## DB
~/AI/openclaw-factory/data/openclaw.db

## Runtime Truth
- 状態は必ずDBから取得
- MDは状態を持たない

## System Structure
- Mainline
- Meta Control
- Business Worker

## Human Role
- 承認
- 外部コミュニケーションのみ

## Execution Rule
1. SINGLE SOURCE確認
2. 既存構造確認
3. 重複判定
4. 統合先決定
5. 実装

## Bot Creation Rule
- 新規作成は禁止
- 既存統合 or mode追加のみ許可

## Absolute Rules
- 同一役割の複数bot禁止
- 既存機能の再実装禁止
- bridge / selector / normalizer 増殖禁止

## Current Focus
1. 重複削減
2. Kaikun04高速化
3. 構造固定
