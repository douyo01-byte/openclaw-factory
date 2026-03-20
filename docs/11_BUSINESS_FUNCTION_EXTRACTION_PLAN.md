# BUSINESS FUNCTION EXTRACTION PLAN

## scout_market_v2
### expected reusable areas
- source loading
- rss fetch
- item scoring
- contact extraction
- item save / seen management

## chat_research_v1
### expected reusable areas
- url normalize
- page fetch
- signal extraction
- summary build
- contact enqueue
- role_briefs update
- chat_jobs consume / complete

## integration rule
- 単体 bot として復活しない
- 関数単位で mainline に吸収する
- items / contacts / chat_jobs / role_briefs を触る処理だけを分離対象にする
- Telegram送信や常駐 loop は統合先で再設計する

## next implementation order
1. scout_market_v2 の純関数を抽出
2. chat_research_v1 の純関数を抽出
3. DB更新関数を分離
4. mainline へ最小差分で統合
