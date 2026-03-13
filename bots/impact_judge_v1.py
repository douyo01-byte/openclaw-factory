from __future__ import annotations
import os, time, sqlite3, json

DB_PATH = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = int(os.environ.get("IMPACT_JUDGE_SLEEP", "20"))
LIMIT = int(os.environ.get("IMPACT_JUDGE_LIMIT", "20"))

CRITICAL_TARGETS = (
    "dev_command_executor",
    "dev_pr_watcher",
    "dev_pr_automerge",
    "dev_merge_notify",
    "spec_refiner",
    "self_healing",
    "db_integrity",
    "ops_brain",
    "chat_router",
    "meeting_orchestrator",
    "learning_brain",
)

HIGH_WORDS = (
    "timeout", "retry", "rollback", "lock", "deadlock", "crash", "hang",
    "telegram", "sqlite", "database", "db", "merge", "watcher", "executor",
    "state", "notify", "error", "exception", "guard", "backoff"
)

def conn():
    c = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    try:
        c.execute("pragma journal_mode=WAL")
    except Exception:
        pass
    try:
        c.execute("pragma synchronous=NORMAL")
    except Exception:
        pass
    return c

def ensure_schema(c):
    cols = {r["name"] for r in c.execute("pragma table_info(dev_proposals)").fetchall()}
    if "impact_score" not in cols:
        c.execute("alter table dev_proposals add column impact_score real default 0")
    if "impact_level" not in cols:
        c.execute("alter table dev_proposals add column impact_level text default ''")
    if "impact_reason" not in cols:
        c.execute("alter table dev_proposals add column impact_reason text default ''")
    if "impact_updated_at" not in cols:
        c.execute("alter table dev_proposals add column impact_updated_at text default ''")
    c.execute("""
    create table if not exists ceo_hub_events(
      id integer primary key,
      event_type text,
      title text,
      body text,
      proposal_id integer,
      pr_url text,
      created_at text default (datetime('now')),
      sent_at text
    )
    """)

def score_row(r):
    title = (r["title"] or "").lower()
    target = (r["target_system"] or "").lower()
    improvement = (r["improvement_type"] or "").lower()
    result_score = float(r["result_score"] or 0)

    score = 3
    reasons = []

    if improvement in ("guard", "bugfix"):
        score += 2
        reasons.append("不具合や停止を防ぐ修正")
    elif improvement in ("optimization", "performance"):
        score += 1
        reasons.append("処理効率を上げる修正")
    elif improvement in ("refactor", "logging", "diagnostics"):
        score += 1
        reasons.append("保守や調査をしやすくする修正")

    if any(x in target for x in CRITICAL_TARGETS):
        score += 2
        reasons.append("開発基盤の重要部分への変更")

    if any(x in title for x in HIGH_WORDS):
        score += 1
        reasons.append("障害や通信不安定に効く内容")

    if result_score >= 0.9:
        score += 1
        reasons.append("学習評価も高め")

    score = max(1, min(score, 10))

    if score >= 8:
        level = "high"
        level_ja = "高"
    elif score >= 5:
        level = "medium"
        level_ja = "中"
    else:
        level = "low"
        level_ja = "低"

    if not reasons:
        reasons.append("通常の内部改善")

    reason = " / ".join(reasons[:3])
    return score, level, level_ja, reason

def body_text(r, score, level_ja, reason):
    return "\n".join([
        f"impact_level={level_ja}",
        f"impact_score={score}",
        f"target_system={(r['target_system'] or '').strip()}",
        f"improvement_type={(r['improvement_type'] or '').strip()}",
        f"source_ai={(r['source_ai'] or '').strip()}",
        f"reason={reason}",
    ])

def tick():
    c = conn()
    try:
        ensure_schema(c)
        rows = c.execute("""
        select
          id, title, target_system, improvement_type, source_ai,
          pr_url, result_score, status, dev_stage, pr_status,
          coalesce(impact_level,'') as impact_level
        from dev_proposals
        where coalesce(status,'')='merged'
          and coalesce(dev_stage,'')='merged'
          and coalesce(pr_status,'')='merged'
          and coalesce(impact_level,'')=''
          and coalesce(source_ai,'')<>''
          and lower(coalesce(title,'')) not like 'mothership:%'
        order by id desc
        limit ?
        """, (LIMIT,)).fetchall()

        done = 0
        for r in rows:
            score, level, level_ja, reason = score_row(r)
            c.execute("""
            update dev_proposals
            set impact_score=?,
                impact_level=?,
                impact_reason=?,
                impact_updated_at=datetime('now')
            where id=?
            """, (score, level, reason, r["id"]))

            exists = c.execute("""
            select 1
            from ceo_hub_events
            where event_type='impact_judged'
              and proposal_id=?
            limit 1
            """, (r["id"],)).fetchone()

            if not exists:
                c.execute("""
                insert into ceo_hub_events(event_type,title,body,proposal_id,pr_url,created_at)
                values(?,?,?,?,?,datetime('now'))
                """, (
                    "impact_judged",
                    f"改善インパクト評価 : {r['title']}",
                    body_text(r, score, level_ja, reason),
                    r["id"],
                    r["pr_url"] or "",
                ))
            done += 1
            print(f"[impact_judge] proposal={r['id']} level={level} score={score} reason={reason}", flush=True)

        if done:
            c.commit()
    finally:
        c.close()

def main():
    while True:
        try:
            tick()
        except Exception as e:
            print(f"[impact_judge] err {e!r}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
