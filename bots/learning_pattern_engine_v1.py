import sqlite3,os,time

DB=os.environ.get("OCLAW_DB_PATH")

def extract_patterns(conn):

    rows=conn.execute("""
    select category,target_system,improvement_type,count(*) as c
    from dev_proposals
    where status='merged'
    group by category,target_system,improvement_type
    order by c desc
    limit 10
    """).fetchall()

    patterns=[]

    for r in rows:
        cat=r[0] or ""
        tgt=r[1] or ""
        imp=r[2] or ""
        c=r[3]

        summary=f"{cat}+{tgt}+{imp} success={c}"
        patterns.append(summary)

    return patterns

def main():

    conn=sqlite3.connect(DB)

    while True:
        try:

            patterns=extract_patterns(conn)

            for p in patterns:

                conn.execute("""
                insert into ceo_hub_events
                (event_type,title)
                values (?,?)
                """,
                (
                "learning_pattern",
                p
                ))

                print(f"[learning_pattern] {p}",flush=True)

            conn.commit()

        except Exception as e:
            print(f"[learning_pattern_error] {e}",flush=True)

        time.sleep(1800)

if __name__=="__main__":
    main()
