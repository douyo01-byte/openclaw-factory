import sqlite3,os,time,random

DB=os.environ.get("OCLAW_DB_PATH")

ideas=[
"Optimize database query batching",
"Improve executor stability",
"Add automated PR validation",
"Improve CI pipeline caching",
"Add test coverage analyzer",
"Refactor dev_executor batching logic",
"Improve PR merge safety checks",
"Add automated code quality scan",
"Improve git conflict detection",
"Add executor retry mechanism"
]

def main():
    conn=sqlite3.connect(DB)
    while True:
        try:
            title=random.choice(ideas)

            conn.execute("""
            insert into dev_proposals
            (title,description,status,category,target_system)
            values (?,?,?,?,?)
            """,
            (
            title,
            title,
            "idea",
            "automation",
            "core"
            ))

            conn.commit()

            print(f"[code_supply] {title}",flush=True)

        except Exception as e:
            print(f"[code_supply_error] {e}",flush=True)

        time.sleep(900)

if __name__=="__main__":
    main()
