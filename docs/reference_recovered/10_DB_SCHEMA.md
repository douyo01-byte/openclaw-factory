# OpenClaw DB Schema Notes

## 重要テーブル

- dev_proposals
- proposal_state
- proposal_conversation
- inbox_commands
- decisions
- ceo_hub_events

## 現在の概算件数

- dev_proposals: 808
- proposal_state: refined=11 / merged=2 / executed=1 / pr_created=1 を確認
- proposal_conversation: 約50〜100
- inbox_commands: 少数
- decisions: 数百
- ceo_hub_events: merged=50 / learning_result=4 / pr_created=3

## proposal_state の主な状態

- waiting_answer
- execute_now
- archive

過去痕跡:
- answer_received
- refined
- executed
- pr_created

## ceo_hub_events

カラム:
- id
- event_type
- title
- body
- proposal_id
- pr_url
- created_at
- sent_at

注意:
- type カラムは存在しない

現況:
- merged: 50
- learning_result: 4
- pr_created: 3

## DB/SQLルール

1. DB は実体が symlink のことがある
2. factory と daemon が同じ DB を見ているか毎回確認
3. sqlite3 の .tables は SQL ではなく dot command
4. proposal_state と dev_proposals を混同しない
5. inbox_commands は Telegram 実画面と照合する
6. done でも実返信が無ければ成功扱いしない
7. tg_offset は進みすぎると update を飛ばす
8. status が空 / processed=0 の残骸を定期確認
9. migration は列存在確認してから
10. answer_received / waiting_answer / refined / executed / pr_created / execute_now / archive の意味を毎回揃える
11. SQL手動更新は最後の手段
