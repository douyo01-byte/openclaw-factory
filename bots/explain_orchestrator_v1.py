import os, sqlite3

FACTORY_DB = os.environ.get("FACTORY_DB_PATH") or os.path.expanduser("~/AI/openclaw-factory//Users/doyopc/AI/openclaw-factory-daemon/data/openclaw_real.db")

def fconn():
    c = sqlite3.connect(FACTORY_DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA busy_timeout=30000")
    return c

def ensure_tables(c):
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

def jp_title(title):
    m = {
        "Improve Research Quality": "調査品質の改善",
        "Speed Pipeline": "実行速度の改善",
        "Optimize Costs": "運用コストの改善",
        "Improve Monitoring": "監視品質の改善",
        "Executor Stability": "executor安定化",
    }
    return m.get(title, title)

def short_text(spec, explain):
    s = (spec or "").strip().replace("\n", " ")
    e = (explain or "").strip().replace("\n", " ")
    if len(s) > 70:
        s = s[:70] + "..."
    if len(e) > 70:
        e = e[:70] + "..."
    if e:
        return f"仕様: {s} / AI意図: {e}"
    return f"仕様: {s}"

def run_once():
    sent = 0
    with fconn() as f:
        ensure_tables(f)
        rows = f.execute("""
            select id, title, coalesce(spec,'') as spec, coalesce(explain,'') as explain
            from dev_proposals
            where coalesce(explain_stage,'')='generated'
            order by id asc
            limit 20
        """).fetchall()
        for r in rows:
            title = jp_title((r["title"] or "").strip())
            body = short_text(r["spec"], r["explain"])
            exists = f.execute("""
                select 1 from ceo_hub_events
                where event_type='explain_generated'
                  and proposal_id=?
                limit 1
            """, (r["id"],)).fetchone()
            if not exists:
                f.execute("""
                    insert into ceo_hub_events(event_type,title,body,proposal_id)
                    values('explain_generated',?,?,?)
                """, (f"仕様整理: {title}", body, r["id"]))
            f.execute("""
                update dev_proposals
                set explain_stage='sent'
                where id=?
            """, (r["id"],))
            sent += 1
        f.commit()
    print(f"explain_buffered={sent}", flush=True)

if __name__ == "__main__":
    run_once()
