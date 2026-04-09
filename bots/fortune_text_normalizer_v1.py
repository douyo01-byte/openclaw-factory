from pathlib import Path
import re

TARGETS = [
    Path("data/fortune/lp/trial_1_lp.html"),
    Path("data/fortune/offers/trial_1_offer.txt"),
]

JP = r'[ぁ-んァ-ン一-龥ーA-Za-z0-9¥]'
PAT = re.compile(rf'({JP})\s+({JP})')

def normalize_text(s: str) -> str:
    while PAT.search(s):
        s = PAT.sub(r'\1\2', s)
    s = re.sub(r' {2,}', ' ', s)
    return s

def main():
    for p in TARGETS:
        if not p.exists():
            continue
        s = p.read_text(encoding="utf-8", errors="ignore")
        p.write_text(normalize_text(s), encoding="utf-8")
        print(f"normalized={p}", flush=True)

if __name__ == "__main__":
    main()
