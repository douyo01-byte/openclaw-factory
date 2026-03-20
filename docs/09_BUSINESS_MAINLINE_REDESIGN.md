# BUSINESS MAINLINE REDESIGN

## purpose
brain_supply_v1 退役後の business 系統合先を固定する。

## current policy
- 単体 bot 復活は禁止
- 新規 bot 追加は禁止
- business 機能は mainline 統合前提でのみ再開
- ingest_private_replies_kaikun02 / ingest_private_replies_kaikun04 は intake 専用で維持

## integration candidates
### scout source
- jp.openclaw.scout_market_v2
- status: code exists / runtime retired
- decision: mainline再設計対象

### research source
- jp.openclaw.chat_research_v1
- status: code exists / runtime retired
- decision: mainline再設計対象

## fixed interpretation
- scout_market_v2 は items 候補収集ロジック源
- chat_research_v1 は chat_jobs / role_briefs / contacts 強化ロジック源
- どちらも単体復活ではなく、既存 mainline へ吸収して再設計する

## temporary business live set
- jp.openclaw.ingest_private_replies_kaikun02
- jp.openclaw.ingest_private_replies_kaikun04

## next implementation target
1. ops_brain / mainline のどちらを business 統合先にするか確定
2. scout_market_v2 から再利用関数を抽出
3. chat_research_v1 から再利用関数を抽出
4. 単体 LaunchAgent を増やさず統合実装する
