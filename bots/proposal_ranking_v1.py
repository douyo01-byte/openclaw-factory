from __future__ import annotations
import os
import sqlite3
import time

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or "data/openclaw.db"

IMPACT_W = {"high": 24, "medium": 14, "low": 6, "": 0}
RISK_W = {"low": 10, "medium": 4, "high": -8, "": 0}
COMPLEXITY_W = {"low": 8, "medium": 3, "high": -6, "": 0}
SYS_W = {"core": 18, "business": 10, "codebase": 8, "learning": 8, "product": 6, "": 0}

def parse_discussion(msg: str):
    d = {}
    for line in (msg or "").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            d[k.strip().lower()] = v.strip().lower()
    return d

def compute_score(row, convo):
    base = int(row["quality_score"] or 0)
    info = {}
    for r in convo:
        if (r["role"] or "") == "discussion":
            info = parse_discussion(r["message"] or "")
    impact = info.get("impact", "")
    risk = info.get("risk", "")
    complexity = info.get("complexity", "")
    system_importance = info.get("system_importance", row["target_system"] or "")
    score = (
        base
        + IMPACT_W.get(impact, 0)
        + RISK_W.get(risk, 0)
        + COMPLEXITY_W.get(complexity, 0)
        + SYS_W.get(system_importance, 0)
    )
    detail = f"impact={impact or '-'} risk={risk or '-'} complexity={complexity or '-'} system={system_importance or '-'}"
    return score, detail

def main():
    conn = sqlite3.connect(DB, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass

    rows = conn.execute("""
    select id, title, category, target_system, improvement_type, quality_score, status
    from dev_proposals
    where coalesce(status,'') in ('idea','approved')
    order by id desc
    limit 300
    """).fetchall()

    for r in rows:
        convo = conn.execute("""
        select role, message
        from proposal_conversation
        where proposal_id=?
        order by id asc
        """, (r["id"],)).fetchall()
        score, detail = compute_score(r, convo)
        conn.execute("""
        update dev_proposals
        set priority=?
        where id=?
        """, (score, r["id"]))
        print(f"[ranking] proposal={r['id']} score={score} {detail}", flush=True)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    while True:
        main()
        time.sleep(60)



def fetch_learning_bias(conn, row):
    try:
        cat = (row["category"] or "").strip()
    except Exception:
        cat = (row.get("category") or "").strip() if hasattr(row, "get") else ""
    try:
        tgt = (row["target_system"] or "").strip()
    except Exception:
        tgt = (row.get("target_system") or "").strip() if hasattr(row, "get") else ""
    try:
        imp = (row["improvement_type"] or "").strip()
    except Exception:
        imp = (row.get("improvement_type") or "").strip() if hasattr(row, "get") else ""

    rows = conn.execute("""
    select coalesce(title,'')
    from ceo_hub_events
    where event_type='learning_pattern'
    order by id desc
    limit 200
    """).fetchall()

    bias = 0
    hits = []

    for r in rows:
        title = (r[0] or "").strip()
        if not title:
            continue
        key = f"{cat}+{tgt}+{imp}"
        key2 = f"{cat}+{tgt}"
        key3 = f"{cat}+"
        if key and key in title:
            bias = max(bias, 20)
            hits.append(key)
        elif key2 and key2 in title:
            bias = max(bias, 14)
            hits.append(key2)
        elif key3 and key3 in title:
            bias = max(bias, 8)
            hits.append(key3)

    return bias, hits

def compute_ranking(row):
    import sqlite3, os
    db = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH")
    bias = 0
    hits = []
    if db:
        try:
            conn = sqlite3.connect(db)
            bias, hits = fetch_learning_bias(conn, row)
            conn.close()
        except Exception:
            bias = 0
            hits = []

    g = globals()
    for name in (
        "rank_proposal",
        "rank_row",
        "score_proposal",
        "score_row",
        
        "proposal_score",
    ):
        fn = g.get(name)
        if callable(fn):
            out = fn(row)
            if isinstance(out, tuple) and len(out) >= 2:
                return int(out[0]), str(out[1])
            try:
                return int(out), f"via={name}"
            except Exception:
                pass
    def _get(k, d=""):
        try:
            v = row[k]
        except Exception:
            try:
                v = row.get(k, d)
            except Exception:
                v = d
        return d if v is None else v
    quality = int(_get("quality_score", 0) or 0)
    category = (_get("category", "") or "").strip().lower()
    target = (_get("target_system", "") or "").strip().lower()
    improvement = (_get("improvement_type", "") or "").strip().lower()
    priority = int(_get("priority", 0) or 0)

    score = quality + priority
    reasons = [f"quality={quality}", f"priority={priority}"]

    if category == "automation":
        score += 8
        reasons.append("category=8")
    elif category == "improvement":
        score += 6
        reasons.append("category=6")
    elif category == "research":
        score += 4
        reasons.append("category=4")
    else:
        reasons.append("category=0")

    if target in ("core", "codebase", "dev_executor", "brain", "product"):
        score += 6
        reasons.append("target=6")
    else:
        reasons.append("target=0")

    if improvement in ("stabilize", "resilience", "safety"):
        score += 6
        reasons.append("improvement=6")
    elif improvement:
        score += 3
        reasons.append("improvement=3")
    else:
        reasons.append("improvement=0")

    return score, ",".join(reasons)

