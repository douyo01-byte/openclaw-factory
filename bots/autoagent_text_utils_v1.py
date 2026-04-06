import re
import unicodedata

JP = r"一-龥ぁ-んァ-ヶー々〆ヵヶ"

def clean_text(text: str) -> str:
    t = unicodedata.normalize("NFKC", text or "")
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = t.replace("\u3000", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)

    lines = []
    for line in t.split("\n"):
        s = line.strip()

        prev = None
        while prev != s:
            prev = s
            s = re.sub(rf"([{JP}])\s+([{JP}])", r"\1\2", s)

        s = re.sub(r"\s+([:：、。,.!?）\]】])", r"\1", s)
        s = re.sub(r"([（\[\【])\s+", r"\1", s)
        s = re.sub(r"[ ]{2,}", " ", s)
        lines.append(s)

    t = "\n".join(lines)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()

def clean_list(items):
    return [x for x in (clean_text(i) for i in (items or [])) if x]

def pretty_runtime_summary(text: str) -> str:
    t = clean_text(text)
    t = t.replace("EXEC:", "EXEC:\n")
    t = t.replace("JOB:", "\nJOB:\n")
    t = t.replace("ADOPTION:", "\nADOPTION:\n")
    t = re.sub(r"(done=\d+)(new=\d+)", r"\1\n\2", t)
    t = re.sub(r"(new=\d+)(skipped=\d+)", r"\1\n\2", t)
    t = re.sub(r"(skipped=\d+)(failed=\d+)", r"\1\n\2", t)
    t = re.sub(r"(reject=\d+)(hold=\d+)", r"\1\n\2", t)
    t = re.sub(r"(hold=\d+)(adopt=\d+)", r"\1\n\2", t)
    return clean_text(t)

def strip_task_header(text: str) -> str:
    t = clean_text(text)
    t = re.sub(r"^\[TASK_ID:\d+\]\s*", "", t)
    return t.strip()
