import sqlite3,datetime,random

DB="data/openclaw.db"

ideas=[
("Improve Research Quality","Add better search sources","dev/idea-a-%s"%pid),
("Optimize Costs","Add cost estimator","dev/idea-b-%s"%pid),
("Speed Pipeline","Parallelize jobs","dev/idea-c-%s"%pid)
]

def main():
    pid=None

    conn=sqlite3.connect(DB)
    cur=conn.cursor()
    pid=int(datetime.datetime.utcnow().timestamp())
    t=random.choice(ideas)
    cur.execute("""insert into dev_proposals(title,description,branch_name,status)
                   values(?,?,?,?)""",(t[0],t[1],(t[2]%pid),"approved"))
    conn.commit()
    print("proposal created")

if __name__=="__main__":
    main()
