# OpenClaw File Policy

1. factory は本体設計・中核ロジック
2. daemon は運用・常駐・Telegram・監視寄り
3. exec は一時的・実験的・分離実行用
4. 同じ役割のコードを repo 跨ぎで増やしすぎない
5. 現役は1個に寄せる
6. bak は本番ディレクトリに溜めすぎず archive へ移す
7. broken は残すより archive 化して隔離
8. pyc しかないものは存在ではなく再構築候補として扱う
