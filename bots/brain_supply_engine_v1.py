import sqlite3,os,time,random

DB=os.environ.get("OCLAW_DB_PATH")

ideas=[
"Improve proposal scoring architecture",
"Introduce learning pattern clustering",
"Optimize AI meeting reasoning loop",
"Improve proposal ranking signals",
"Add reinforcement learning for executor",
"Improve AI conversation memory",
"Improve spec refinement reasoning",
"Add proposal quality predictor",
"Improve AI planning architecture",
"Optimize learning feedback loop"
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
            "research",
            "core"
            ))

            conn.commit()

            print(f"[brain_supply] {title}",flush=True)

        except Exception as e:
            print(f"[brain_supply_error] {e}",flush=True)

        time.sleep(1200)

if __name__=="__main__":
    main()
