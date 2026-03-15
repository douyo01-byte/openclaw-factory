import sqlite3,time,traceback,os

DB="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
LIMIT=int(os.environ.get("OPEN_PR_LIMIT","25"))
SLEEP=int(os.environ.get("OPEN_PR_GUARD_SLEEP","60"))

def tick():
    conn=sqlite3.connect(DB, timeout=60)
    conn.execute("pragma busy_timeout=60000")

    open_total=conn.execute("""
    select count(distinct pr_url)
    from dev_proposals
    where coalesce(pr_status,'')='open'
      and coalesce(pr_url,'')<>''
    """).fetchone()[0]

    trimmed = 0

    if open_total > LIMIT:
        trimmed = open_total - LIMIT
        conn.execute("""
        with pr_rank as (
          select
            pr_url,
            min(
              case coalesce(source_ai,'')
                when 'cto' then 0
                when 'mothership' then 1
                when 'strategy_engine' then 2
                when 'innovation_engine' then 3
                else 9
              end
            ) as pri,
            max(created_at) as latest_created_at,
            max(id) as max_id
          from dev_proposals
          where coalesce(pr_status,'')='open'
            and coalesce(pr_url,'')<>''
          group by pr_url
        ),
        keep as (
          select pr_url
          from pr_rank
          order by pri asc, latest_created_at desc, max_id desc
          limit ?
        )
        update dev_proposals
        set
          status='closed',
          dev_stage='closed',
          pr_status='closed',
          processing=0
        where coalesce(pr_status,'')='open'
          and coalesce(pr_url,'')<>''
          and coalesce(pr_url,'') not in (select pr_url from keep);
        """, (LIMIT,))
        conn.commit()

    open_after=conn.execute("""
    select count(distinct pr_url)
    from dev_proposals
    where coalesce(pr_status,'')='open'
      and coalesce(pr_url,'')<>''
    """).fetchone()[0]

    conn.close()
    print(f"open_prs={open_total} limit={LIMIT} trimmed={trimmed} after={open_after}", flush=True)

def main():
    print("boot_ok", flush=True)
    while True:
        ok = False
        for i in range(5):
            try:
                tick()
                ok = True
                break
            except sqlite3.OperationalError as e:
                print(f"retry i={i} err={e!r}", flush=True)
                time.sleep(3)
            except Exception as e:
                print(repr(e), flush=True)
                print(traceback.format_exc(), flush=True)
                break
        if not ok:
            print("guard_cycle_failed", flush=True)
        time.sleep(SLEEP)

if __name__=="__main__":
    main()
