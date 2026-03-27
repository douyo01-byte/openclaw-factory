#!/usr/bin/env python3
import json
import re
import sys
from text_normalizer_v1 import normalize_text

URL_RE = re.compile(r'https?://\S+')

def resolve_context(text: str) -> dict:
    raw = text
    t = normalize_text(text)
    tl = t.lower()
    urls = URL_RE.findall(raw)
    target_object = ""
    if "educateb" in tl.replace(" ", ""):
        target_object = "educate B"
    has_continue_intent = any(x in t for x in ["続き","そのまま","次へ","改善","作り直し","深掘り"])
    return {
        "normalized_text": t,
        "urls": urls,
        "target_object": target_object,
        "has_continue_intent": has_continue_intent,
    }

def main() -> None:
    text = sys.stdin.read().strip()
    print(json.dumps(resolve_context(text), ensure_ascii=False))

if __name__ == "__main__":
    main()
