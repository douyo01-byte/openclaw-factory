from pathlib import Path
import json
import re
from bs4 import BeautifulSoup

TXT_TARGETS = [
    Path("data/fortune/offers/trial_1_offer.txt"),
    Path("data/fortune/delivery/trial_1_delivery_template.txt"),
]

JSON_TARGETS = [
    Path("data/fortune/forms/trial_1_order_form.json"),
]

HTML_TARGETS = [
    Path("data/fortune/lp/trial_1_lp.html"),
]

JP = r'[ぁ-んァ-ン一-龥ーA-Za-z0-9¥]'
PAT = re.compile(rf'({JP})\s+({JP})')

def normalize_text(s: str) -> str:
    while PAT.search(s):
        s = PAT.sub(r'\1\2', s)
    s = re.sub(r' {2,}', ' ', s)
    return s

def normalize_json_obj(v):
    if isinstance(v, dict):
        return {k: normalize_json_obj(val) for k, val in v.items()}
    if isinstance(v, list):
        return [normalize_json_obj(x) for x in v]
    if isinstance(v, str):
        return normalize_text(v)
    return v

def normalize_html(path: Path):
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    for node in soup.find_all(string=True):
        parent = getattr(node, "parent", None)
        if parent and parent.name in ("script", "style"):
            continue
        raw = str(node)
        fixed = normalize_text(raw)
        if fixed != raw:
            node.replace_with(fixed)
    path.write_text(str(soup), encoding="utf-8")

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

    for p in HTML_TARGETS:
        if p.exists():
            normalize_html(p)
            print(f"normalized_html={p}", flush=True)

if __name__ == "__main__":
    main()
