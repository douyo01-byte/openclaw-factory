import sqlite3
from datetime import datetime

DB = "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def ensure():
    with conn() as c:
        c.execute("""
        create table if not exists adoption_actions (
          id integer primary key autoincrement,
          candidate_id integer not null,
          action text not null default '',
          status text not null default 'new',
          created_at text default (datetime('now')),
          unique(candidate_id, action)
        )
        """)
        c.commit()

def run_once():
    ensure()
    done = 0
    with conn() as c:
        rows = c.execute("""
        select id, title, url, source, score, status
        from adoption_candidates
        where status='adopt'
        order by id desc
        limit 20
        """).fetchall()

        for r in rows:
            candidate_id = int(r["id"])
            exists = c.execute("""
            select 1 from adoption_actions
            where candidate_id=? and action='ceo_hub_proposal'
            """, (candidate_id,)).fetchone()
            if exists:
                continue

            body = "\n".join([
                "【 TECH ADOPTION 候補 】",
                f"title: {r['title']}",
                f"source: {r['source']}",
                f"score: {r['score']}",
                f"url: {r['url']}",
                "",
                "【 判定 】",
                "無料・ローカル優先方針で採用候補",
                "",
                "【 次アクション案 】",
                "- docs_only",
                "- experiment",
                "- integrate_now",
            ])

            c.execute("""
            insert into ceo_hub_events(source, source_key, title, body, level, created_at)
            values(?,?,?,?,?,datetime('now'))
            """, (
                "tech_adoption_adopter_v1",
                f"adoption_candidate:{candidate_id}",
                f"TECH ADOPTION CANDIDATE #{candidate_id}",
                body,
                "info",
            ))

            c.execute("""
            insert into adoption_actions(candidate_id, action, status)
            values(?, 'ceo_hub_proposal', 'done')
            """, (candidate_id,))
            done += 1

        c.commit()

    print(f"adoption_adopter_done={done}", flush=True)

if __name__ == "__main__":
    run_once()
