import os
import sqlite3
import re
import math
import collections

DB = os.environ.get("DB_PATH", "data/openclaw.db")

BAD = {
    "http","https","www","openclaw","system","latest","window","actions",
    "decision","reason","score","adopted","held","dropped","item",
    "reflection_worker_v1","db_updated","git_push","git_base","picked",
    "dev","cli","workspace","main","branch","proposal","open","merged",
    "2026","2025","10z"
}

ALLOW_HINT = {
    "pipeline","speed","logging","merge","executor","automation","safety","security",
    "optimize","costs","improve","research","quality"
}

def tok(s):
    s = (s or "").lower()
    out = []
    out += re.findall(r"[a-z0-9][a-z0-9_\-]{2,}", s)
    out += re.findall(r"(?:https?://)?(?:www\.)?([a-z0-9\-]+\.[a-z0-9\.\-]+)", s)
    out += re.findall(r"[ァ-ヴー]{2,}", s)
    out += re.findall(r"[一-龥]{2,}", s)
    out += re.findall(r"[ぁ-ん]{3,}", s)
    cleaned = []
    for x in out:
        x = x.strip("._- ")
        if not x or x in BAD:
            continue
        if re.fullmatch(r"\d+", x):
            continue
        if re.search(r"\d{4}", x):
            continue
        cleaned.append(x)
    return cleaned


def load_learning_results(conn):
    try:
        rows = conn.execute("""
            select
              lower(coalesce(pattern,'')) as pattern,
              coalesce(score,0) as score
            from learning_results
            where coalesce(pattern,'') <> ''
            order by coalesce(score,0) desc
            limit 200
        """).fetchall()
        return [(r[0], float(r[1] or 0)) for r in rows]
    except Exception:
        return []

def merge_learning_into_scores(scored, learning_rows):
    extra = {}
    for pat, sc in learning_rows:
        for tok in (pat or "").split():
            tok = tok.strip()
            if len(tok) < 2:
                continue
            extra[tok] = extra.get(tok, 0.0) + min(max(sc / 20.0, -3.0), 3.0)
    merged = []
    for tok, base in scored:
        merged.append((tok, base + extra.pop(tok, 0.0)))
    for tok, w in extra.items():
        merged.append((tok, w))
    merged.sort(key=lambda x: abs(x[1]), reverse=True)
    return merged

def main():
    conn = sqlite3.connect(DB)
    conn.execute(
        "create table if not exists decision_patterns(token text primary key, weight real not null, updated_at text default (datetime('now')))"
    )

    pos = collections.Counter()
    neg = collections.Counter()

    has_decision_events = conn.execute(
        "select count(*) from sqlite_master where type='table' and name='decision_events'"
    ).fetchone()[0]
    rows = []
    if has_decision_events:
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

    has_retrospectives = conn.execute(
        "select count(*) from sqlite_master where type='table' and name='retrospectives'"
    ).fetchone()[0]
    retro_rows = []
    if has_retrospectives:
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

        if abs(s) < 0.2:
            continue
        if w not in ALLOW_HINT and (p + n) < 2:
            continue

        scored.append((w, s))

    scored.sort(key=lambda x: abs(x[1]), reverse=True)
    learning_rows = load_learning_results(conn)
    scored = merge_learning_into_scores(scored, learning_rows)
    top = scored[:80]

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
