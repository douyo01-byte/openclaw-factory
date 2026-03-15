import os, time, sqlite3

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
LIMIT_NEW = int(os.environ.get("PROPOSAL_LIMIT_NEW", "20"))
LIMIT_APPROVED = int(os.environ.get("PROPOSAL_LIMIT_APPROVED", "10"))
SLEEP = int(os.environ.get("PROPOSAL_THROTTLE_SLEEP", "300"))

def main():
    while True:
        try:
            conn = sqlite3.connect(DB, timeout=30)
            conn.execute("pragma busy_timeout=30000")
            new_n = conn.execute("select count(*) from dev_proposals where coalesce(status,'')='new'").fetchone()[0]
            approved_n = conn.execute("select count(*) from dev_proposals where coalesce(status,'')='approved'").fetchone()[0]

            if new_n > LIMIT_NEW:
                conn.execute("""
                update dev_proposals
                set status='throttled'
                where id in (
                  select id
                  from dev_proposals
                  where coalesce(status,'')='new'
                  order by created_at asc, id asc
                  limit ?
                )
                """, (new_n - LIMIT_NEW,))

            if approved_n > LIMIT_APPROVED:
                conn.execute("""
                update dev_proposals
                set status='throttled'
                where id in (
                  select id
                  from dev_proposals
                  where coalesce(status,'')='approved'
                    and coalesce(source_ai,'') not in ('innovation_engine','strategy_engine')
                  order by created_at asc, id asc
                  limit ?
                )
                """, (approved_n - LIMIT_APPROVED,))

            conn.commit()
            conn.close()
            print("throttle_checked", flush=True)
        except Exception as e:
            print(repr(e), flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
