from pathlib import Path
import json
import re

TXT_TARGETS = [
    Path("data/fortune/offers/trial_1_offer.txt"),
    Path("data/fortune/delivery/trial_1_delivery_template.txt"),
]

JSON_TARGETS = [
    Path("data/fortune/forms/trial_1_order_form.json"),
]

JP = r'[ぁ-んァ-ン一-龥ー]'
PAT = re.compile(rf'({JP})\s+({JP})')

def normalize_text(s: str) -> str:
    while PAT.search(s):
        s = PAT.sub(r'\1\2', s)
    s = re.sub(r'[ \t]{2,}', ' ', s)
    return s

def normalize_json_obj(v):
    if isinstance(v, dict):
        return {k: normalize_json_obj(val) for k, val in v.items()}
    if isinstance(v, list):
        return [normalize_json_obj(x) for x in v]
    if isinstance(v, str):
        return normalize_text(v)
    return v

def main():
    for p in TXT_TARGETS:
        if p.exists():
            s = p.read_text(encoding="utf-8", errors="ignore")
            p.write_text(normalize_text(s), encoding="utf-8")
            print(f"normalized_txt={p}", flush=True)

    for p in JSON_TARGETS:
        if p.exists():
            obj = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
            obj = normalize_json_obj(obj)
            p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"normalized_json={p}", flush=True)

if __name__ == "__main__":
    main()
