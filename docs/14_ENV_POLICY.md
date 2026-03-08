# OpenClaw Env Policy

1. 古い token は信用しない
2. env は repoごとに役割を分ける
3. 何を source するかを loop 内で明示する
4. 単体実行時は必ず source 手順込みで実行する
5. TELEGRAM_BOT_TOKEN empty を見落とさない
6. DB_PATH は毎回確認する
7. FACTORY_DB_PATH と DB_PATH のズレを作らない
8. launchctl 環境変数と shell 環境変数を混同しない
9. env の bak は archive 候補
10. 新しい token 導入後は旧 token を止める前提で整理する
