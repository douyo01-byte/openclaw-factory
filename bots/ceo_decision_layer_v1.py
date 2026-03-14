from __future__ import annotations
import os, sys, time, sqlite3

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = int(os.environ.get("CEO_DECISION_LAYER_SLEEP", "60"))
LIMIT = int(os.environ.get("CEO_DECISION_LAYER_LIMIT", "200"))

CRITICAL_TARGETS = (
    "dev_command_executor",
    "dev_pr_watcher",
    "dev_pr_automerge",
    "dev_merge_notify",
    "spec_refiner",
    "self_healing",
    "db_integrity",
    "chat_router",
    "meeting_orchestrator",
    "learning_brain",
    "command_apply",
)

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    try:
        c.execute("pragma journal_mode=WAL")
    except Exception:
        pass
    return c

def ensure_schema(c):
    c.execute("""
    create table if not exists ceo_decision_layer_results(
      proposal_id integer primary key,
      rank_score real default 0,
      meeting_needed integer default 0,
      decision_bucket text default '',
      summary text default '',
      source_snapshot text default '',
      updated_at text default (datetime('now'))
    )
    """)
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

def cols(c, table):
    return {r["name"] for r in c.execute(f"pragma table_info({table})").fetchall()}

def expr(name, all_cols):
    if name in all_cols:
        if name in ("result_score", "impact_score"):
            return f"coalesce({name},0) as {name}"
        return f"coalesce({name},'') as {name}"
    if name in ("result_score", "impact_score"):
        return f"0 as {name}"
    return f"'' as {name}"

def score_row(r):
    score = 0.0
    status = (r["status"] or "").lower()
    dev_stage = (r["dev_stage"] or "").lower()
    target = (r["target_system"] or "").lower()
    source_ai = (r["source_ai"] or "").lower()
    improvement = (r["improvement_type"] or "").lower()
    title = (r["title"] or "").lower()
    result_score = float(r["result_score"] or 0)
    impact_score = float(r["impact_score"] or 0)
    priority = float(r["priority"] or 0)

    if status in ("execute_now", "approved", "new", "open"):
        score += 2
    if dev_stage in ("execute_now", "approved", "ready", "pr_created", "open"):
        score += 2
    if any(x in target for x in CRITICAL_TARGETS):
        score += 3
    if source_ai in ("ceo", "cto", "coo"):
        score += 2
    if improvement in ("guard", "bugfix"):
        score += 2
    if improvement in ("optimization", "performance", "refactor", "diagnostics", "logging"):
        score += 1
    if "security" in title or "rollback" in title or "lock" in title or "timeout" in title:
        score += 1
    score += min(result_score, 2.0)
    score += min(impact_score / 4.0, 2.0)
    score += min(priority / 10.0, 3.0)

    meeting_needed = 1 if (
        score >= 6
        or any(x in target for x in CRITICAL_TARGETS)
        or source_ai in ("ceo", "cto", "coo")
    ) else 0

    if score >= 8:
        bucket = "now"
    elif score >= 5:
        bucket = "soon"
    elif score >= 3:
        bucket = "review"
    else:
        bucket = "hold"

    summary = " | ".join([
        f"status={status}",
        f"dev_stage={dev_stage}",
        f"target={r['target_system'] or ''}",
        f"improvement={r['improvement_type'] or ''}",
        f"source_ai={r['source_ai'] or ''}",
        f"result_score={result_score}",
        f"impact_score={impact_score}",
        f"priority={priority}",
    ])

    return round(score, 2), meeting_needed, bucket, summary

def tick():
    c = conn()
    try:
        ensure_schema(c)
        all_cols = cols(c, "dev_proposals")
        wanted = [
            "id","title","target_system","improvement_type","source_ai",
            "status","dev_stage","pr_status","pr_url","result_score",
            "impact_score","priority","created_at"
        ]
        sel = ",\n          ".join(expr(x, all_cols) for x in wanted)
        rows = c.execute(f"""
        select
          {sel}
        from dev_proposals
        where coalesce(status,'') not in ('merged','closed','done')
          and coalesce(dev_stage,'') not in ('merged','closed','done')
        order by id desc
        limit ?
        """, (LIMIT,)).fetchall()

        done = 0
        for r in rows:
            rank_score, meeting_needed, bucket, summary = score_row(r)
            snapshot = "|".join([
                str(r["id"]),
                r["title"] or "",
                r["target_system"] or "",
                r["improvement_type"] or "",
                r["source_ai"] or "",
                r["status"] or "",
                r["dev_stage"] or "",
                r["pr_status"] or "",
            ])
            c.execute("""
            insert into ceo_decision_layer_results(
              proposal_id, rank_score, meeting_needed, decision_bucket,
              summary, source_snapshot, updated_at
            ) values(?,?,?,?,?,?,datetime('now'))
            on conflict(proposal_id) do update set
              rank_score=excluded.rank_score,
              meeting_needed=excluded.meeting_needed,
              decision_bucket=excluded.decision_bucket,
              summary=excluded.summary,
              source_snapshot=excluded.source_snapshot,
              updated_at=datetime('now')
            """, (r["id"], rank_score, meeting_needed, bucket, summary, snapshot))

            if bucket in ("now", "soon"):
                ex = c.execute("""
                select 1
                from ceo_hub_events
                where event_type='ceo_decision_layer'
                  and proposal_id=?
                limit 1
                """, (r["id"],)).fetchone()
                if not ex:
                    body = "\n".join([
                        f"rank_score={rank_score}",
                        f"meeting_needed={meeting_needed}",
                        f"decision_bucket={bucket}",
                        summary,
                    ])
                    c.execute("""
                    insert into ceo_hub_events(event_type,title,body,proposal_id,pr_url,created_at)
                    values(?,?,?,?,?,datetime('now'))
                    """, (
                        "ceo_decision_layer",
                        f"CEO decision layer: {r['title'] or ('proposal ' + str(r['id']))}",
                        body,
                        r["id"],
                        r["pr_url"] or "",
                    ))
            done += 1

        c.commit()
        print(f"[ceo_decision_layer] processed={done}", flush=True)
    finally:
        c.close()

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        tick()
        return
    while True:
        try:
            tick()
        except Exception as e:
            print(f"[ceo_decision_layer] err {e!r}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
