# Asset Reuse Master Plan (2026-03-17)

| path | decision | purpose | exists | last_commit | next_action |
|---|---|---|---|---|---|
| bots/secretary_llm_v1.py | REPURPOSE | CEO向け統合要約専任候補 | yes | cdbdced Use merged runtime classification source in replies | CEO要約専任に責務変更して quick route から分離 |
| bots/chat_research_v1.py | REPURPOSE | 補助調査専任候補 | yes | 2d85838 Reconnect code review and migrate business bots to market tables | 補助調査専任に責務変更して本流直結しない |
| bots/command_apply_v1.py | HOLD | 現本流では未使用 | yes | c0a39a3 ci: auto fix (20260302-224953) | 現状維持。docs に保留理由を固定 |
| bots/meeting_from_db_v1.py | HOLD | 現本流では未使用 | yes | c0a39a3 ci: auto fix (20260302-224953) | 現状維持。docs に保留理由を固定 |
| bots/team/aya_judge.py | REPURPOSE | 役割資産として再利用候補 | yes | c0a39a3 ci: auto fix (20260302-224953) | bot単体運用ではなく役割定義/source_ai資産として再配置 |
| bots/team/daiki_analyst.py | REPURPOSE | 役割資産として再利用候補 | yes | c0a39a3 ci: auto fix (20260302-224953) | bot単体運用ではなく役割定義/source_ai資産として再配置 |
| bots/team/kenji_researcher.py | REPURPOSE | 役割資産として再利用候補 | yes | c0a39a3 ci: auto fix (20260302-224953) | bot単体運用ではなく役割定義/source_ai資産として再配置 |
| bots/team/miho_finder.py | REPURPOSE | 役割資産として再利用候補 | yes | c0a39a3 ci: auto fix (20260302-224953) | bot単体運用ではなく役割定義/source_ai資産として再配置 |
| bots/team/sakura_scout.py | REPURPOSE | 役割資産として再利用候補 | yes | c0a39a3 ci: auto fix (20260302-224953) | bot単体運用ではなく役割定義/source_ai資産として再配置 |
