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
              lower(trim(
                coalesce(title,'') || ' ' ||
                coalesce(source_ai,'') || ' ' ||
                coalesce(target_system,'') || ' ' ||
                coalesce(improvement_type,'') || ' ' ||
                coalesce(impact_reason,'') || ' ' ||
                coalesce(result_type,'') || ' ' ||
                coalesce(result_note,'') || ' ' ||
                coalesce(learning_summary,'')
              )) as learning_text,
              coalesce(result_score,0) as result_score,
              coalesce(impact_score,0) as impact_score,
              coalesce(success_flag,0) as success_flag
            from learning_results
            order by id desc
            limit 500
        """).fetchall()
        out = []
        for learning_text, result_score, impact_score, success_flag in rows:
            text = str(learning_text or '').strip()
            if not text:
                continue
            score = float(result_score or 0) + float(impact_score or 0)
            if int(success_flag or 0) == 1:
                score += 2.0
            else:
                score -= 1.0
            out.append((text, score))
        return out
    except Exception:
        return []

def merge_learning_into_scores(scored, learning_rows):
    extra = {}
    blocked_prefixes = ("impact=", "result=", "source_ai=", "target=", "type=")
    blocked_exact = {
        "success", "merged", "normal", "change", "code_change",
        "source_ai", "target", "type", "impact", "result", "low", "medium", "high",
        "core", "after", "with", "and", "state", "audit", "loop", "self",
        "idea_pool", "backfilled", "innovation", "automation"
    }
    for pat, sc in learning_rows:
        for token in tok(pat or ""):
            token = token.strip().lower()
            if len(token) < 4:
                continue
            if token in blocked_exact:
                continue
            if any(token.startswith(x) for x in blocked_prefixes):
                continue
            extra[token] = extra.get(token, 0.0) + min(max(sc / 160.0, -0.45), 0.45)
    merged = []
    seen = set()
    for token, base in scored:
        w = base + extra.pop(token, 0.0)
        w = min(max(w, -3.0), 3.0)
        merged.append((token, w))
        seen.add(token)
    for token, w in extra.items():
        if token in seen:
            continue
        merged.append((token, min(max(w, -0.6), 0.6)))
    merged.sort(key=lambda x: abs(x[1]), reverse=True)
    return merged


def build_patterns_from_learning_only(learning_rows):
    scores = {}
    for learning_text, sc in learning_rows:
        for token in tok(learning_text or ""):
            token = token.strip()
            if not token:
                continue
            if token in BAD:
                continue
            scores[token] = scores.get(token, 0.0) + min(max(float(sc or 0) / 260.0, -0.22), 0.22)
    out = [(k, v) for k, v in scores.items() if abs(v) >= 0.05]
    out.sort(key=lambda x: abs(x[1]), reverse=True)
    return out

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
