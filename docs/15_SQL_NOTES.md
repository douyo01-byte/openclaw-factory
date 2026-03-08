# OpenClaw SQL Notes

1. DB は実体が symlink のことがある
2. factory と daemon が同じ DB を見ているか毎回確認
3. sqlite3 の .tables は SQL ではなく dot command
4. proposal_state と dev_proposals を混同しない
5. inbox_commands は Telegram 実画面と照合する
6. done でも実返信が無ければ成功扱いしない
7. tg_offset は進みすぎると update を飛ばす
8. status が空 / processed=0 の残骸を定期確認
9. decisions は器があっても件数少の可能性
10. migration は列存在確認してから
11. answer_received / waiting_answer / refined / executed / pr_created の意味を毎回揃える
12. SQL手動更新は最後の手段
