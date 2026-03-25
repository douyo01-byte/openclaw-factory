import re

def check_lp(text):
    ok = True
    reasons = []

    if not re.search(r"(サプリ|商品|サービス|提供)", text):
        ok = False
        reasons.append("何の商品か不明")

    if not re.search(r"(改善|解消|サポート|実現)", text):
        ok = False
        reasons.append("ベネフィット不明確")

    if not re.search(r"(購入|申込|無料|今すぐ)", text):
        ok = False
        reasons.append("CTAなし")

    return ok, reasons

def check_ec(text):
    ok = True
    reasons = []

    if "Before" not in text or "After" not in text:
        ok = False
        reasons.append("Before/Afterなし")

    if not re.search(r"(理由|なぜ)", text):
        ok = False
        reasons.append("改善理由なし")

    return ok, reasons

def check_sns(text):
    ok = True
    reasons = []

    if len(text.split("\n")[0]) > 40:
        ok = False
        reasons.append("フック弱い")

    if "?" not in text and "!" not in text:
        ok = False
        reasons.append("引きが弱い")

    return ok, reasons

def score(ok, reasons):
    if ok:
        return 0.9
    if len(reasons) == 1:
        return 0.75
    return 0.6
