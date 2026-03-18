import os, sqlite3, datetime

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def main():
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")

    rows = con.execute("""
        select
          mi.id,
          coalesce(mi.title,'') as title,
          coalesce(mi.url,'') as url
        from market_items mi
        where not exists (
          select 1
          from market_chat_jobs j
          where j.item_id = mi.id
            and coalesce(j.role,'')='jpcheck'
            and coalesce(j.status,'') in ('new','done')
        )
        order by mi.id desc
        limit 10
    """).fetchall()

    inserted = 0
    for r in rows:
        q = f"日本語対応と連絡先有無を確認: {r['title']} {r['url']}".strip()
        con.execute("""
            insert into market_chat_jobs(
              chat_id,item_id,role,query,status,created_at,updated_at
            ) values(
              ?,?,?,?,'new',datetime('now'),datetime('now')
            )
        """, ("auto-chat-research", r["id"], "jpcheck", q))
        inserted += 1

    con.commit()
    con.close()
    print(f"inserted={inserted}")

if __name__ == "__main__":
    main()
