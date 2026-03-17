# Unconnected Resolution Plan (2026-03-17)

| path | proposed_action | reason | next_step |
|---|---|---|---|
| bots/secretary_llm_v1.py | conditional_restore | Kaikun02 quick routes と役割重複がある | secretary と kaikun02 の責務分離を先に決定 |
| bots/ai_employee_manager_v1.py | restore_candidate | current dev_proposals/source_ai schema と整合しやすい | runner + launchagent 追加候補 |
| bots/ai_employee_ranking_v1.py | restore_candidate | ai_employee_scores 依存で単純、復帰安全性が高い | manager とセットで有効化候補 |
| bots/innovation_llm_engine_v1.py | restore_candidate | 改善案供給の中核候補だが API/env 確認が必要 | env と投入頻度を監査 |
| bots/chat_research_v1.py | hold | 旧 market/business 文脈が強く現本流優先度は低い | 保留として docs 明記 |
