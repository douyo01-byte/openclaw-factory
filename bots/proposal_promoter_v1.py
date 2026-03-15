import sqlite3,time,traceback

DB="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP=20

def tick():
    conn=sqlite3.connect(DB,timeout=30)
    conn.execute("pragma busy_timeout=30000")
    conn.execute("pragma journal_mode=WAL")

    rows=conn.execute("""
    select id,title,coalesce(source_ai,'') as source_ai,coalesce(status,'') as status,
           coalesce(project_decision,'') as project_decision,
           coalesce(dev_stage,'') as dev_stage,
           coalesce(spec_stage,'') as spec_stage,
           coalesce(pr_status,'') as pr_status
    from dev_proposals
    where coalesce(status,'')='approved'
      and (
        coalesce(source_ai,'') in ('innovation_engine','strategy_engine')
        or title like 'MotherShip:%'
      )
      and (
        coalesce(spec_stage,'')='idea'
        or coalesce(dev_stage,'')='idea'
        or (
          coalesce(project_decision,'')=''
          and coalesce(dev_stage,'')=''
          and coalesce(spec_stage,'')=''
          and coalesce(pr_status,'')=''
        )
      )
    order by
      case
        when coalesce(source_ai,'') in ('innovation_engine','strategy_engine') then 0
        when title like 'MotherShip:%' then 1
        else 9
      end,
      id asc
    limit 50""").fetchall()

    done=0
    for r in rows:
        conn.execute("""
        update dev_proposals
        set project_decision='execute_now',
            dev_stage='execute_now',
            spec_stage='raw'
        where id=?
        """,(r[0],))
        done+=1

    if done:
        conn.commit()
    conn.close()
    print(f"promoted={done}", flush=True)

def main():
    print("boot_ok", flush=True)
    while True:
        try:
            tick()
        except Exception as e:
            print(repr(e), flush=True)
            print(traceback.format_exc(), flush=True)
        time.sleep(SLEEP)

if __name__=="__main__":
    main()
