from __future__ import annotations
import os
import sqlite3
import time

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = float(os.environ.get("SELF_IMPROVEMENT_PATTERN_BRIDGE_SLEEP", "15"))

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    try:
        c.execute("pragma journal_mode=WAL")
    except Exception:
        pass
    return c

def cols(c, table: str) -> set[str]:
    return {r["name"] for r in c.execute(f"pragma table_info({table})").fetchall()}

def ensure_cols(c, table: str, adds: dict[str, str]):
    existing = cols(c, table)
    for k, sql in adds.items():
        if k not in existing:
            c.execute(sql)

def ensure_schema(c):
    c.execute("""
        create table if not exists learning_patterns(
          id integer primary key autoincrement,
          pattern_type text not null,
          pattern_key text not null,
          sample_count integer default 0,
          success_count integer default 0,
          avg_impact_score real default 0,
          avg_result_score real default 0,
          weight real default 0,
          updated_at text default (datetime('now')),
          unique(pattern_type, pattern_key)
        )
    """)
    c.execute("""
        create table if not exists success_patterns(
          pattern text primary key,
          score real,
          updated_at text default (datetime('now'))
        )
    """)
    c.execute("""
        create table if not exists self_improvement_pattern_bridge_log(
          id integer primary key autoincrement,
          learning_result_id integer not null unique,
          pattern_key text not null default '',
          status text not null default '',
          reason text not null default '',
          created_at text default (datetime('now')),
          updated_at text default (datetime('now'))
        )
    """)
    ensure_cols(c, "self_improvement_log", {
        "pattern_bridge_status": "alter table self_improvement_log add column pattern_bridge_status text not null default ''",
        "pattern_bridge_reason": "alter table self_improvement_log add column pattern_bridge_reason text not null default ''",
    })

def fetch_rows(c):
    return c.execute("""
        select
          lr.id as learning_result_id,
          lr.proposal_id,
          coalesce(lr.title,'') as title,
          coalesce(lr.source_ai,'') as source_ai,
          coalesce(lr.target_system,'') as target_system,
          coalesce(lr.improvement_type,'') as improvement_type,
          coalesce(lr.impact_score,0) as impact_score,
          coalesce(lr.result_score,0) as result_score,
          coalesce(lr.result_type,'') as result_type,
          coalesce(lr.success_flag,0) as success_flag,
          coalesce(lr.learning_summary,'') as learning_summary,
          sil.id as self_improvement_id
        from learning_results lr
        left join self_improvement_log sil
          on sil.learning_result_id = lr.id
        left join self_improvement_pattern_bridge_log p
          on p.learning_result_id = lr.id
        where coalesce(lr.source_ai,'')='kaikun04'
          and coalesce(lr.target_system,'')='self_improvement_loop'
          and p.learning_result_id is null
        order by lr.id asc
        limit 50
    """).fetchall()

def extract_pattern_key(r) -> str:
    summary = (r["learning_summary"] or "").splitlines()
    fix = ""
    reusable = ""
    for line in summary:
        s = line.strip()
        if s.startswith("fix="):
            fix = s[len("fix="):].strip()
        elif s.startswith("reusable_pattern="):
            reusable = s[len("reusable_pattern="):].strip()
    if fix:
        return fix
    if reusable:
        return reusable
    it = (r["improvement_type"] or "").strip()
    rt = (r["result_type"] or "").strip()
    if it or rt:
        return f"{it}:{rt}".strip(":")
    return "self_improvement:unknown"

def upsert_learning_pattern(c, pattern_key: str, r):
    row = c.execute("""
        select
          id, sample_count, success_count, avg_impact_score, avg_result_score
        from learning_patterns
        where pattern_type='self_improvement_exec'
          and pattern_key=?
    """, (pattern_key,)).fetchone()

    impact = float(r["impact_score"] or 0)
    result_score = float(r["result_score"] or 0)
    success = 1 if int(r["success_flag"] or 0) == 1 else 0

    if row:
        sample_count = int(row["sample_count"] or 0) + 1
        success_count = int(row["success_count"] or 0) + success
        prev_ai = float(row["avg_impact_score"] or 0)
        prev_ar = float(row["avg_result_score"] or 0)
        avg_impact = ((prev_ai * (sample_count - 1)) + impact) / sample_count
        avg_result = ((prev_ar * (sample_count - 1)) + result_score) / sample_count
        weight = round((success_count / sample_count) * avg_result, 6) if sample_count else 0
        c.execute("""
            update learning_patterns
            set sample_count=?,
                success_count=?,
                avg_impact_score=?,
                avg_result_score=?,
                weight=?,
                updated_at=datetime('now')
            where id=?
        """, (sample_count, success_count, avg_impact, avg_result, weight, row["id"]))
    else:
        sample_count = 1
        success_count = success
        avg_impact = impact
        avg_result = result_score
        weight = round((success_count / sample_count) * avg_result, 6)
        c.execute("""
            insert into learning_patterns(
              pattern_type, pattern_key, sample_count, success_count,
              avg_impact_score, avg_result_score, weight, updated_at
            ) values(
              'self_improvement_exec', ?, ?, ?, ?, ?, ?, datetime('now')
            )
        """, (pattern_key, sample_count, success_count, avg_impact, avg_result, weight))

def upsert_success_pattern(c, pattern_key: str, r):
    score = float(r["result_score"] or 0)
    ok = int(r["success_flag"] or 0)
    if ok != 1:
        return
    row = c.execute("select score from success_patterns where pattern=?", (pattern_key,)).fetchone()
    if row:
        prev = float(row["score"] or 0)
        new_score = round((prev + score) / 2, 6)
        c.execute("""
            update success_patterns
            set score=?, updated_at=datetime('now')
            where pattern=?
        """, (new_score, pattern_key))
    else:
        c.execute("""
            insert into success_patterns(pattern, score, updated_at)
            values(?, ?, datetime('now'))
        """, (pattern_key, score))

def mark_done(c, learning_result_id: int, pattern_key: str, self_improvement_id: int | None):
    c.execute("""
        insert into self_improvement_pattern_bridge_log(
          learning_result_id, pattern_key, status, reason, created_at, updated_at
        ) values(
          ?, ?, 'done', '', datetime('now'), datetime('now')
        )
    """, (learning_result_id, pattern_key))
    if self_improvement_id:
        c.execute("""
            update self_improvement_log
            set pattern_bridge_status='done',
                pattern_bridge_reason='',
                updated_at=datetime('now')
            where id=?
        """, (self_improvement_id,))

def mark_skipped(c, learning_result_id: int, pattern_key: str, reason: str, self_improvement_id: int | None):
    c.execute("""
        insert into self_improvement_pattern_bridge_log(
          learning_result_id, pattern_key, status, reason, created_at, updated_at
        ) values(
          ?, ?, 'skipped', ?, datetime('now'), datetime('now')
        )
    """, (learning_result_id, pattern_key, reason))
    if self_improvement_id:
        c.execute("""
            update self_improvement_log
            set pattern_bridge_status='skipped',
                pattern_bridge_reason=?,
                updated_at=datetime('now')
            where id=?
        """, (reason, self_improvement_id))

def tick():
    done = 0
    skipped = 0
    with conn() as c:
        ensure_schema(c)
        rows = fetch_rows(c)
        for r in rows:
            learning_result_id = int(r["learning_result_id"])
            self_improvement_id = r["self_improvement_id"]
            pattern_key = extract_pattern_key(r).strip()
            if not pattern_key:
                mark_skipped(c, learning_result_id, "", "empty_pattern_key", self_improvement_id)
                skipped += 1
                continue
            try:
                upsert_learning_pattern(c, pattern_key, r)
                upsert_success_pattern(c, pattern_key, r)
                mark_done(c, learning_result_id, pattern_key, self_improvement_id)
                done += 1
            except Exception as e:
                mark_skipped(c, learning_result_id, pattern_key, f"{type(e).__name__}:{e}", self_improvement_id)
                skipped += 1
        c.commit()
    print(f"[self_improvement_pattern_bridge_v1] done={done} skipped={skipped}", flush=True)

def main():
    while True:
        try:
            tick()
        except Exception as e:
            print(f"[self_improvement_pattern_bridge_v1] fatal err={e!r}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
