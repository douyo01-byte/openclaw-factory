import os
import re
import math
import sqlite3
import collections

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db")

STOP = {
    "openclaw","proposal","dev","improve","add","auto","for","the","and","with",
    "v1","v2","test","e2e","fix","bot","ai"
}

def tok(s: str):
    s = (s or "").lower()
    s = s.replace("／", "/").replace("　", " ")
    out = []
    out += re.findall(r"[a-z0-9][a-z0-9_\-]{2,}", s)
    out += re.findall(r"[ァ-ヴー]{2,}", s)
    out += re.findall(r"[一-龥]{2,}", s)
    out += re.findall(r"[ぁ-ん]{3,}", s)
    out = [x.strip(".-_/ ") for x in out]
    out = [x for x in out if x and x not in STOP and not x.startswith("http")]
    return out

def main():
    conn = sqlite3.connect(DB, timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
    create table if not exists decision_patterns(
      token text primary key,
      weight real not null,
      updated_at text default (datetime('now'))
    )
    """)
    rows = conn.execute("""
    select
      e.proposal_id,
      coalesce(d.title,'') as title,
      coalesce(d.category,'') as category,
      coalesce(d.target_system,'') as target_system,
      coalesce(d.improvement_type,'') as improvement_type,
      coalesce(e.body,'') as body
    from ceo_hub_events e
    left join dev_proposals d on d.id=e.proposal_id
    where coalesce(e.event_type,'')='learning_result'
    order by e.id desc
    limit 2000
    """).fetchall()

    pos = collections.Counter()
    neg = collections.Counter()

    for _, title, category, target_system, improvement_type, body in rows:
        text = " ".join([title, category, target_system, improvement_type, body])
        tokens = tok(text)
        if not tokens:
            continue
        m = re.search(r"result=([a-zA-Z_]+)", body)
        result = (m.group(1).lower() if m else "")
        if result == "success":
            pos.update(tokens)
        elif result in {"fail", "failed", "error", "bad"}:
            neg.update(tokens)
        elif result == "neutral":
            for t in tokens:
                pos[t] += 0.25
                neg[t] += 0.25

    all_tokens = set(pos.keys()) | set(neg.keys())
    scored = []
    for w in all_tokens:
        p = float(pos[w])
        n = float(neg[w])
        s = math.log(1 + p) - math.log(1 + n)
        if abs(s) < 0.35:
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

if __name__ == "__main__":
    main()
