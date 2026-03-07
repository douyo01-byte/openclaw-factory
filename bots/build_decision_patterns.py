import os
import sqlite3
import re
import math
import collections

DB = os.environ.get("DB_PATH", "data/openclaw.db")

def tok(s):
    s = (s or "").lower()
    out = []
    out += re.findall(r"[a-z0-9][a-z0-9_\-]{2,}", s)
    out += re.findall(r"[一-龥]{2,}", s)
    out += re.findall(r"[ぁ-ん]{3,}", s)
    out += re.findall(r"[ァ-ヴー]{2,}", s)
    return [x for x in out if x]

def main():
    conn = sqlite3.connect(DB)
    conn.execute(
        "create table if not exists decision_patterns(token text primary key, weight real not null, updated_at text default (datetime('now')))"
    )

    rows = conn.execute("""
        select text
        from retrospectives
        order by id desc
        limit 200
    """).fetchall()

    pos = collections.Counter()
    neg = collections.Counter()

    for (text,) in rows:
        text = text or ""
        lines = text.splitlines()
        for line in lines:
            line = line.strip()
            if not line.startswith("- "):
                continue
            ts = tok(line)
            if not ts:
                continue
            if "追 加" in line or "改 善" in line or "チ ェ ッ ク" in line or "見 直 し" in line or "拡 張" in line:
                pos.update(ts)
            else:
                neg.update(ts)

    all_tokens = set(pos.keys()) | set(neg.keys())
    scored = []
    for w in all_tokens:
        p = pos[w]
        n = neg[w]
        s = math.log(1 + p) - math.log(1 + n)
        if abs(s) < 0.01:
            continue
        scored.append((w, s))

    scored.sort(key=lambda x: abs(x[1]), reverse=True)
    top = scored[:120]

    conn.execute("delete from decision_patterns")
    conn.executemany(
        "insert into decision_patterns(token,weight,updated_at) values(?,?,datetime('now'))",
        top,
    )
    conn.commit()
    conn.close()
    print(f"decision_patterns_done={len(top)}", flush=True)

if __name__ == "__main__":
    main()
