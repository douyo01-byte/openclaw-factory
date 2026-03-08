# OpenClaw Docs Index

このdocsはOpenClawの母艦正本。
古いチャット、古い引き継ぎ、断片メモより、まずこのdocsを優先する。

##最初に読む順番

1. 01_SYSTEM_PROMPT.md
2. 02_MASTER_PLAN.md
3. 03_MOTHERSHIP_ROLE.md
4. 06_CURRENT_STATE.md
5. 07_ROADMAP.md
6. 08_HANDOVER.md
7. 05_DEV_RULES.md

必要時のみ読む:
- 04_ARCHITECTURE.md
- 09_BOT_CATALOG.md
- 10_DB_SCHEMA.md
- 11_OPERATIONS.md
- 12_AI_COMPANY.md
- 13_FILE_POLICY.md
- 14_ENV_POLICY.md
- 15_SQL_NOTES.md
- 16_DELETION_POLICY.md
- 17_EFFICIENCY_RULES.md
- 18_REPORT_TEMPLATE.md
- 19_WORK_START_PROMPT.md

##母艦運用の最重要3ファイル

- 01_SYSTEM_PROMPT.md
- 06_CURRENT_STATE.md
- 08_HANDOVER.md

この3つを常に最新化する。
他ファイルは補助資料。

##読み方ルール

-実ファイル・実DB・実ログ・実プロセスを優先
-実在確認前に完成扱いしない
- pycのみはソース実在扱いしない
-構想と実装を混ぜない
-古い情報より新しい確認結果を優先する

## docs更新ルール

-母艦チャットではdocsを更新する
-作業チャットでは実装を進め、最後に08_HANDOVER.md形式で返す
-重要な状態変化は06_CURRENT_STATE.mdに反映する
-長期方針変更は01_SYSTEM_PROMPT.md / 02_MASTER_PLAN.md / 07_ROADMAP.mdに反映する

## archiveルール

- docs直下が正本
- docs/archiveは参照用
- archiveの内容は最新の正とは限らない

##現在の基本認識

- OpenClawはAI事業会社の中にAI開発部門を持つ
-現在は開発部門重視
-今は売上拡大より母艦強化を優先
-外部課金、契約、カード決済は自動化しない
