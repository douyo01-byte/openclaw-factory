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
    out += re.findall(r"(?:https?://)?(?:www\.)?([a-z0-9\-]+\.[a-z0-9\.\-]+)", s)
    out += re.findall(r"[ァ-ヴー]{2,}", s)
    out += re.findall(r"[一-龥]{2,}", s)
    out += re.findall(r"[ぁ-ん]{3,}", s)
    bad = {"http", "https", "www", "openclaw", "system", "latest", "window", "actions"}
    return [x.strip("._- ") for x in out if x and x.strip("._- ") and x.strip("._- ") not in bad]

def main():
    conn = sqlite3.connect(DB)
    conn.execute(
        "create table if not exists decision_patterns(token text primary key, weight real not null, updated_at text default (datetime('now')))"
    )

    pos = collections.Counter()
    neg = collections.Counter()

    rows = conn.execute("""
      select decision, reason
      from decision_events
      order by id desc
      limit 3000
    """).fetchall()

    for decision, reason in rows:
        d = (decision or "").strip().lower()
        tokens = tok(reason or "")
        if not tokens:
            continue
        if d in {"approved", "approve", "go", "merged", "db_updated", "git_push", "picked"}:
            pos.update(tokens)
        elif d in {"hold", "reject", "rejected", "drop", "closed", "archive"}:
            neg.update(tokens)

    retro_rows = conn.execute("""
      select text
      from retrospectives
      order by id desc
      limit 500
    """).fetchall()

    for (text,) in retro_rows:
        tokens = tok(text or "")
        if tokens:
            neg.update(tokens)

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
