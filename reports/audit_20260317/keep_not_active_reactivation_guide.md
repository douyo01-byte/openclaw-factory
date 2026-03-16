# KEEP_NOT_ACTIVE Reactivation Guide (2026-03-17)

この7本は repo に保持するが、現行ACTIVE runtimeには含めない。
再有効化は LaunchAgent / DB / 入出力先 を確認してから行う。

## bots/command_apply_v1.py
- file_exists: yes
- candidate_label: jp.openclaw.command_apply_v1
- launchagent_exists_now: no
- last_commit: c0a39a3 ci: auto fix (20260302-224953)
- code_signals: sqlite3.connect, argparse, decision_, item_meta
- reactivation_requirements: DB schema確認, 旧business系テーブル再定義確認
- recommended_restore_mode: 旧command系テーブルを復元する場合のみ再接続

## bots/meeting_from_db_v1.py
- file_exists: yes
- candidate_label: jp.openclaw.meeting_from_db_v1
- launchagent_exists_now: no
- last_commit: c0a39a3 ci: auto fix (20260302-224953)
- code_signals: sqlite3.connect, role_briefs, items, item_meta
- reactivation_requirements: DB schema確認, market系テーブル整合確認, 旧business系テーブル再定義確認
- recommended_restore_mode: meeting入力元DBを明示して単発運用から再開

## bots/team/aya_judge.py
- file_exists: yes
- candidate_label: jp.openclaw.aya_judge
- launchagent_exists_now: no
- last_commit: c0a39a3 ci: auto fix (20260302-224953)
- code_signals: sqlite3.connect, argparse, decision_, item_meta
- reactivation_requirements: DB schema確認, 旧business系テーブル再定義確認
- recommended_restore_mode: persona系/旧team系として単体再接続

## bots/team/daiki_analyst.py
- file_exists: yes
- candidate_label: jp.openclaw.daiki_analyst
- launchagent_exists_now: no
- last_commit: c0a39a3 ci: auto fix (20260302-224953)
- code_signals: sqlite3.connect, items
- reactivation_requirements: DB schema確認, 旧business系テーブル再定義確認
- recommended_restore_mode: persona系/旧team系として単体再接続

## bots/team/kenji_researcher.py
- file_exists: yes
- candidate_label: jp.openclaw.kenji_researcher
- launchagent_exists_now: no
- last_commit: c0a39a3 ci: auto fix (20260302-224953)
- code_signals: sqlite3.connect, argparse, decision_, role_briefs, items
- reactivation_requirements: DB schema確認, market系テーブル整合確認, 旧business系テーブル再定義確認
- recommended_restore_mode: persona系/旧team系として単体再接続

## bots/team/miho_finder.py
- file_exists: yes
- candidate_label: jp.openclaw.miho_finder
- launchagent_exists_now: no
- last_commit: c0a39a3 ci: auto fix (20260302-224953)
- code_signals: sqlite3.connect, argparse, items
- reactivation_requirements: DB schema確認, 旧business系テーブル再定義確認
- recommended_restore_mode: persona系/旧team系として単体再接続

## bots/team/sakura_scout.py
- file_exists: yes
- candidate_label: jp.openclaw.sakura_scout
- launchagent_exists_now: no
- last_commit: c0a39a3 ci: auto fix (20260302-224953)
- code_signals: sqlite3.connect, argparse, role_briefs, items
- reactivation_requirements: DB schema確認, market系テーブル整合確認, 旧business系テーブル再定義確認
- recommended_restore_mode: persona系/旧team系として単体再接続

