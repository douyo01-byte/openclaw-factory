# Reserve Reclassification (2026-03-17)

## ACTIVE_MISCLASSIFIED
- bots/chat_research_v1.py
- bots/db_integrity_check_v1.py
- bots/healthcheck_v1.py
- bots/open_pr_guard_v1.py

## TRUE_RESERVE_KEEP
- bots/command_apply_v1.py
- bots/meeting_from_db_v1.py
- bots/team/aya_judge.py
- bots/team/daiki_analyst.py
- bots/team/kenji_researcher.py
- bots/team/miho_finder.py
- bots/team/sakura_scout.py

## JUDGMENT
- ACTIVE_HITS detected files must be treated as runtime-connected.
- They should be removed from RESERVE_IMPLEMENTED classification.
- TRUE_RESERVE_KEEP are implemented but not connected to current active runtime.
