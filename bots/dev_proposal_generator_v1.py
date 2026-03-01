import sqlite3,datetime,random

DB="data/openclaw.db"

ideas=[
("Improve Research Quality","Add better search sources",f"dev/idea-a-{pid}"),
("Optimize Costs","Add cost estimator",f"dev/idea-b-{pid}"),
("Speed Pipeline","Parallelize jobs",f"dev/idea-c-{pid}")
]

def main():
    conn=sqlite3.connect(DB)
    cur=conn.cursor()
    t=random.choice(ideas)
    cur.execute("""insert into dev_proposals(title,description,branch_name,status)
                   values(?,?,?,?)""",(t[0],t[1],t[2],"approved"))
    conn.commit()
    print("proposal created")

if __name__=="__main__":
    main()
