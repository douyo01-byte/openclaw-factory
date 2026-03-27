#!/usr/bin/env python3
import re
import sys

JOINABLE_RE = re.compile(r'(?<=[ぁ-んァ-ン一-龥a-zA-Z0-9])\s+(?=[ぁ-んァ-ン一-龥a-zA-Z0-9])')
MULTISPACE_RE = re.compile(r'[ \t]+')
MULTINL_RE = re.compile(r'\n{3,}')

def normalize_text(text: str) -> str:
    t = text.replace('\u3000', ' ')
    t = t.replace('\r\n', '\n').replace('\r', '\n')
    t = MULTISPACE_RE.sub(' ', t)
    prev = None
    while prev != t:
        prev = t
        t = JOINABLE_RE.sub('', t)
    t = re.sub(r' +\n', '\n', t)
    t = re.sub(r'\n +', '\n', t)
    t = MULTINL_RE.sub('\n\n', t)
    return t.strip()

def main() -> None:
    print(normalize_text(sys.stdin.read()), end="")

if __name__ == "__main__":
    main()
