#!/usr/bin/env python3
import re
import sys

def normalize_text(text: str) -> str:
    t = text.replace("\u3000", " ")
    t = re.sub(r'[ \t]+', ' ', t)
    t = re.sub(r'(?<=[ぁ-んァ-ン一-龥A-Za-z0-9])\s+(?=[ぁ-んァ-ン一-龥A-Za-z0-9])', '', t)
    return t.strip()

def main() -> None:
    print(normalize_text(sys.stdin.read()), end="")

if __name__ == "__main__":
    main()
