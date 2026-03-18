import os
import time
import sqlite3
import subprocess
from pathlib import Path

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
ROOT = Path("/Users/doyopc/AI/openclaw-factory-daemon")
FACTORY = Path("/Users/doyopc/AI/openclaw-factory")

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    c.execute("pragma journal_mode=WAL")
    return c

def ensure_schema(c):
    c.execute("""
    create table if not exists system_metrics (
      key text primary key,
      value text,
      updated_at text default (datetime('now'))
    )
    """)
    c.execute("""
    create table if not exists ai_intelligence (
      metric text primary key,
      value real
    )
    """)
    c.execute("""
    create table if not exists learning_patterns (
      id integer primary key autoincrement,
      pattern_type text,
      pattern_key text,
      sample_count integer default 0,
      success_count integer default 0,
      avg_impact_score real default 0,
      avg_result_score real default 0,
      weight real default 0,
      updated_at text default (datetime('now'))
    )
    """)
    c.execute("""
    create table if not exists ceo_hub_events (
      id integer primary key autoincrement,
      event_type text,
      title text,
      body text,
      proposal_id integer,
      pr_url text,
      created_at text default (datetime('now')),
      sent_at text
    )
    """)

def one(c, sql, params=()):
    r = c.execute(sql, params).fetchone()
    return r[0] if r and r[0] is not None else 0

def kv_get(c, key, default=""):
    r = c.execute("select value from system_metrics where key=?", (key,)).fetchone()
    return r[0] if r else default

def kv_set(c, key, value):
    c.execute("""
    insert into system_metrics(key, value, updated_at)
    values(?, ?, datetime('now'))
    on conflict(key) do update set
      value=excluded.value,
      updated_at=datetime('now')
    """, (key, str(value)))

def compute_metrics(c):
    total = one(c, "select count(*) from dev_proposals")
    merged = one(c, "select count(*) from dev_proposals where coalesce(status,'')='merged'")
    open_pr = one(c, "select count(*) from dev_proposals where coalesce(pr_status,'')='open'")
    raw_exec = one(c, """
    select count(*) from dev_proposals
    where coalesce(project_decision,'')='execute_now'
      and coalesce(dev_stage,'')='execute_now'
      and coalesce(spec_stage,'')='raw'
    """)
    ready_exec = one(c, """
    select count(*) from dev_proposals
    where coalesce(project_decision,'')='execute_now'
      and coalesce(spec_stage,'')='decomposed'
      and coalesce(pr_status,'')='ready'
    """)
    ceo_events = one(c, "select count(*) from ceo_hub_events")
    merge_rate = (merged / total) if total else 0.0
    return {
        "total": total,
        "merged": merged,
        "open_pr": open_pr,
        "raw_exec": raw_exec,
        "ready_exec": ready_exec,
        "ceo_events": ceo_events,
        "merge_rate": round(merge_rate, 4),
    }

def store_metrics(c, m):
    for k, v in m.items():
        kv_set(c, f"self_evolution.{k}", v)
    c.execute("""
    insert into ai_intelligence(metric, value)
    values('merge_rate', ?)
    on conflict(metric) do update set value=excluded.value
    """, (m["merge_rate"],))

def maybe_emit_event(c, m):
    prev_raw = int(kv_get(c, "self_evolution.prev_raw_exec", "0") or 0)
    prev_ready = int(kv_get(c, "self_evolution.prev_ready_exec", "0") or 0)
    prev_merged = int(kv_get(c, "self_evolution.prev_merged", "0") or 0)

    msgs = []
    if m["raw_exec"] > prev_raw:
        msgs.append(f"execute_now raw backlog increased: {prev_raw} -> {m['raw_exec']}")
    if m["ready_exec"] > prev_ready:
        msgs.append(f"executor-ready proposals increased: {prev_ready} -> {m['ready_exec']}")
    if m["merged"] > prev_merged:
        msgs.append(f"merged proposals increased: {prev_merged} -> {m['merged']}")

    if msgs:
        c.execute("""
        insert into ceo_hub_events(event_type, title, body, created_at)
        values(?, ?, ?, datetime('now'))
        """, (
            "self_evolution",
            "Self evolution status update",
            "\n".join(msgs),
        ))

    kv_set(c, "self_evolution.prev_raw_exec", m["raw_exec"])
    kv_set(c, "self_evolution.prev_ready_exec", m["ready_exec"])
    kv_set(c, "self_evolution.prev_merged", m["merged"])

def maybe_run_docs_sync():
    p = Path("/Users/doyopc/AI/openclaw-factory-docs/scripts/run_docs_sync_v1.sh")
    if p.exists():
        subprocess.run(["/bin/bash", str(p)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def loop():
    while True:
        try:
            with conn() as c:
                ensure_schema(c)
                m = compute_metrics(c)
                store_metrics(c, m)
                maybe_emit_event(c, m)
                c.commit()
            maybe_run_docs_sync()
            print(f"self_evolution tick total={m['total']} merged={m['merged']} open_pr={m['open_pr']} raw={m['raw_exec']} ready={m['ready_exec']}", flush=True)
        except Exception as e:
            print(f"self_evolution error: {e!r}", flush=True)
        time.sleep(300)

if __name__ == "__main__":
    loop()
