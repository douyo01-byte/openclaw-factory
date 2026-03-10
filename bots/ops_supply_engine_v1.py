import sqlite3,os,time,random

DB=os.environ.get("OCLAW_DB_PATH")

ideas=[
"Improve dashboard consistency checks",
"Add watcher failure alerting",
"Improve executor queue observability",
"Add DB drift detection",
"Improve monitoring reliability pipeline",
"Add dashboard data validation",
"Improve infra logging structure",
"Add executor health metrics",
"Improve workflow observability",
"Add automation reliability monitor"
]

def main():
    conn=sqlite3.connect(DB)
    while True:
        try:
            title=random.choice(ideas)

            conn.execute("""
            insert into dev_proposals
            (title,description,status,category,target_system,improvement_type)
            values (?,?,?,?,?,?)
            """,
            (
            title,
            title,
            "idea",
            "ops",
            random.choice(["core","dashboard"]),
            random.choice(["observability","reliability"])
            ))

            conn.commit()

            print(f"[ops_supply] {title}",flush=True)

        except Exception as e:
            print(f"[ops_supply_error] {e}",flush=True)

        time.sleep(1000)

if __name__=="__main__":
    main()
