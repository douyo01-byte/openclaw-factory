# BUSINESS INTEGRATION DECISION

## conclusion
business 統合先は ops_brain ではなく mainline とする。

## reason
- ops_brain は 監視 / health / restart / escalation の運用中枢
- business ロジックを ops_brain に混ぜると責務が壊れる
- scout / research は items / chat_jobs / role_briefs / contacts 系の業務処理
- したがって business は mainline 側へ統合する

## fixed rule
- ops_brain に business 機能を入れない
- business 機能は mainline の既存処理へ統合する
- 単体 LaunchAgent の復活は禁止
- 再利用は関数抽出 → mainline統合 の順で行う

## source mapping
### scout_market_v2
- source role: items候補収集
- target: future business mainline function

### chat_research_v1
- source role: contacts / role_briefs / chat_jobs処理
- target: future business mainline function

## preserved live path
- ingest_private_replies_kaikun02
- ingest_private_replies_kaikun04

## next action
1. scout_market_v2 の再利用関数一覧化
2. chat_research_v1 の再利用関数一覧化
3. mainline へ入れる最小単位で分解
4. 統合実装前に責務を docs で固定
