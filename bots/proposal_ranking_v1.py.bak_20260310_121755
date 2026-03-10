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
