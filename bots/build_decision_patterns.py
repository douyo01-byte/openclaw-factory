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
    "2026","2025","10z",
    "source_ai","target","type","impact","result","core","and","with","after",
    "bots","loop","guard","medium","low","normal","change","code_change",
    "mothership","innovation_llm_engine_v1","brain_supply","idea_pool",
    "kaikun04","cto","v1.py","v2.py"
,
    "high",
    "success",
    "state",
    "audit",
    "self",
    "backfilled",
    "innovation",
    "automation"}

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
              coalesce(title,'') as title,
              coalesce(source_ai,'') as source_ai,
              coalesce(target_system,'') as target_system,
              coalesce(improvement_type,'') as improvement_type,
              coalesce(impact_reason,'') as impact_reason,
              coalesce(result_type,'') as result_type,
              coalesce(result_note,'') as result_note,
              coalesce(learning_summary,'') as learning_summary,
              coalesce(result_score,0) as result_score,
              coalesce(impact_score,0) as impact_score,
              coalesce(success_flag,0) as success_flag
            from learning_results
            order by id desc
            limit 500
        """).fetchall()
        out = []
        for title, source_ai, target_system, improvement_type, impact_reason, result_type, result_note, learning_summary, result_score, impact_score, success_flag in rows:
            parts = [
                str(title or '').strip(),
                str(source_ai or '').strip(),
                str(target_system or '').strip(),
                str(improvement_type or '').strip(),
                str(impact_reason or '').strip(),
                str(result_type or '').strip(),
                str(result_note or '').strip(),
                str(learning_summary or '').strip(),
            ]
            text = " ".join([x for x in parts if x]).strip().lower()
            if not text:
                continue
            score = float(result_score or 0) + float(impact_score or 0)
            if int(success_flag or 0) == 1:
                score += 1.5
            else:
                score -= 0.5
            out.append((text, score))
        return out
    except Exception:
        return []

def merge_learning_into_scores(scored, learning_rows):
    extra = {}
    blocked = {
        "success","merged","normal","change","code_change",
        "low","medium","high","result","impact","source_ai","target","type",
        "mothership","brain_supply","innovation_llm_engine_v1","cto","ceo",
        "core","idea_pool"
    }
    for pat, sc in learning_rows:
        for token in tok(pat or ""):
            token = token.strip().lower()
            if len(token) < 4:
                continue
            if token in blocked:
                continue
            extra[token] = extra.get(token, 0.0) + min(max(sc / 180.0, -0.35), 0.35)
    merged = []
    seen = set()
    for token, base in scored:
        w = base + extra.pop(token, 0.0)
        merged.append((token, max(min(w, 3.0), -3.0)))
        seen.add(token)
    for token, w in extra.items():
        if token in seen:
            continue
        merged.append((token, max(min(w, 0.6), -0.6)))
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
    top = [x for x in scored if abs(x[1]) >= 0.08][:80]
    if not top:
        top = build_patterns_from_learning_only(learning_rows)[:80]

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
