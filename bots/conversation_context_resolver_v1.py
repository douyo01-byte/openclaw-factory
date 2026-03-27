#!/usr/bin/env python3
import json
import re
from typing import Any

URL_RE = re.compile(r'https?://\S+')

def resolve_context(text: str) -> dict[str, Any]:
    urls = URL_RE.findall(text)
    target_object = ""
    if "educate b" in text.lower():
        target_object = "educate B"
    return {
        "urls": urls,
        "target_object": target_object,
        "has_continue_intent": any(x in text for x in ["続き","そのまま","次へ","改善","作り直し","深掘り"]),
    }

def main() -> None:
    import sys
    text = sys.stdin.read().strip()
    print(json.dumps(resolve_context(text), ensure_ascii=False))

if __name__ == "__main__":
    main()
