import re

def parse_approval(text):
    m = re.search(r"承認します\s*#(\d+)", text or "")
    return int(m.group(1)) if m else None

def parse_diff(text):
    m = re.search(r"diff\s*#(\d+)", text or "", flags=re.IGNORECASE)
    return int(m.group(1)) if m else None

def parse_test_only(text):
    m = re.search(r"テストだけ\s*#(\d+)", text or "")
    return int(m.group(1)) if m else None
