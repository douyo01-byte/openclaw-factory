# openclaw-factory
Mac miniでOpenClawを24/7運用するための運用リポジトリ。

提案→PR→自動マージ: Telegramで「提案: <内容>」を送る → dev_proposalsに登録 → 「承認します #<id>」でapproved → PR作成・通知 → マージ後にstatus=mergedへ更新。


## 2026-03-14 status
OpenClaw includes an autonomous improvement loop:

merge -> impact -> learning_results -> learning_patterns -> supply_bias -> self_improvement -> CEO hub -> command_apply -> executor
