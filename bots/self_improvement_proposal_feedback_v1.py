from __future__ import annotations
import os
import sqlite3

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    try:
        c.execute("pragma journal_mode=WAL")
    except Exception:
        pass
    return c

def load_proposal_pattern_hints(limit: int = 8) -> str:
    try:
        with conn() as c:
            rows = c.execute(
                """
                select pattern_type, pattern_key, sample_count, success_count, weight
                from learning_patterns
                where coalesce(pattern_type,'')='self_improvement_exec'
                order by weight desc, success_count desc, sample_count desc, id desc
                limit ?
                """,
                (int(limit),),
            ).fetchall()
            sp = c.execute(
                """
                select pattern, score
                from success_patterns
                where coalesce(pattern,'') like 'script=%'
                order by score desc, updated_at desc
                limit ?
                """,
                (int(limit),),
            ).fetchall()
    except Exception:
        rows = []
        sp = []

    lines = []
    seen = set()

    for r in rows:
        k = (r["pattern_key"] or "").strip()
        if not k or k in seen:
            continue
        seen.add(k)
        lines.append(
            f"- {k} weight={float(r['weight'] or 0):.3f} success={int(r['success_count'] or 0)}/{int(r['sample_count'] or 0)}"
        )

    for r in sp:
        k = (r["pattern"] or "").strip()
        if not k or k in seen:
            continue
        seen.add(k)
        lines.append(f"- {k} score={float(r['score'] or 0):.3f}")

    if not lines:
        return ""

    return "\n".join([
        "再  利  用  可  能  な  成  功  パ  タ  ー  ン  :",
        *lines,
        "提  案  は  具  体  的  に  書  く  こ  と  。",
        "実  行  が  不  要  な  と  き  は  EXEC を  出  さ  な  い  こ  と  。",
        "実  行  が  必  要  な  と  き  だ  け  allowlisted script を  末  尾  に  1つ だ け  出  す  こ  と  。",
    ])

def load_negative_exec_hints(limit: int = 5) -> str:
    try:
        with conn() as c:
            rows = c.execute(
                """
                select pattern_key, weight, sample_count, success_count
                from learning_patterns
                where pattern_type='self_improvement_exec'
                  and coalesce(weight,0) <= 0
                order by sample_count desc, id desc
                limit ?
                """,
                (int(limit),),
            ).fetchall()
    except Exception:
        rows = []

    hints = []
    for r in rows:
        key = (r["pattern_key"] or "").strip()
        if not key:
            continue
        hints.append(
            f"- {key} weight={float(r['weight'] or 0):.3f} success={int(r['success_count'] or 0)}/{int(r['sample_count'] or 0)}"
        )

    if not hints:
        return ""

    return "\n".join([
        "避  け  る  べ  き  EXEC パ  タ  ー  ン  :",
        *hints,
        "上  記  に  寄  る  と  き  は  EXEC を  出  さ  な  い  こ  と  。",
    ])

def load_positive_exec_hints(limit: int = 5) -> str:
    try:
        with conn() as c:
            rows = c.execute(
                """
                select pattern_key, weight, sample_count, success_count
                from learning_patterns
                where pattern_type='self_improvement_exec'
                  and coalesce(weight,0) > 0
                order by weight desc, success_count desc, sample_count desc, id desc
                limit ?
                """,
                (int(limit),),
            ).fetchall()
    except Exception:
        rows = []

    hints = []
    for r in rows:
        key = (r["pattern_key"] or "").strip()
        if not key.startswith("script="):
            continue
        hints.append(
            f"- {key} weight={float(r['weight'] or 0):.3f} success={int(r['success_count'] or 0)}/{int(r['sample_count'] or 0)}"
        )

    if not hints:
        return ""

    return "\n".join([
        "再  利  用  可  能  な  成  功  EXEC パ  タ  ー  ン  :",
        *hints,
        "実  行  が  不  要  な  と  き  は  EXEC を  出  さ  な  い  こ  と  。",
        "実  行  が  必  要  な  と  き  だ  け  allowlisted script を  末  尾  に  1つ だ け  出  す  こ  と  。",
    ])

def build_exec_feedback_block() -> str:
    neg = load_negative_exec_hints()
    pos = load_positive_exec_hints()
    parts = [x for x in (neg, pos) if x]
    return "\n\n".join(parts).strip()
