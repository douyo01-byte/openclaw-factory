#!/usr/bin/env python3
import json
import re
from typing import Any

CREATIVE_KEYWORDS = [
    "lp","ランディングページ","商品分析","勝ち軸","コピー","バナー","画像","動画台本","構成","訴求","記事","紹介文","サムネ"
]
DEV_KEYWORDS = [
    "実装","修正","バグ","テスト","pr","リファクタ","デプロイ","反映","コード","仕様","開発"
]
ANALYZE_KEYWORDS = [
    "分析","調査","整理","比較","抽出","評価","レビュー"
]

def classify(text: str) -> dict[str, Any]:
    t = text.lower()
    score_creative = sum(1 for k in CREATIVE_KEYWORDS if k in t)
    score_dev = sum(1 for k in DEV_KEYWORDS if k in t)
    score_analyze = sum(1 for k in ANALYZE_KEYWORDS if k in t)
    if re.search(r'https?://', text):
        score_analyze += 1
    if score_creative >= max(score_dev, score_analyze):
        domain = "creative"
    elif score_dev >= max(score_creative, score_analyze):
        domain = "development"
    else:
        domain = "analysis"
    return {
        "domain": domain,
        "score_creative": score_creative,
        "score_dev": score_dev,
        "score_analyze": score_analyze,
    }

def main() -> None:
    import sys
    text = sys.stdin.read().strip()
    print(json.dumps(classify(text), ensure_ascii=False))

if __name__ == "__main__":
    main()
