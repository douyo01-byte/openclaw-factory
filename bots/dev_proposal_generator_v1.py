import sqlite3,datetime,random

DB="data/openclaw.db"

IDEAS=[
("Improve Research Quality","Add better search sources","dev/idea-a"),
("Optimize Costs","Add cost estimator","dev/idea-b"),
("Speed Pipeline","Parallelize jobs","dev/idea-c"),]
def main():
    pid=int(datetime.datetime.utcnow().timestamp())

    pid=None

    conn=sqlite3.connect(DB)
    cur=conn.cursor()
    pid=int(datetime.datetime.utcnow().timestamp())
    t=random.choice(IDEAS)
    cur.execute("""insert into dev_proposals(title,description,branch_name,status)
                   values(?,?,?,?)""",(t[0],t[1],(t[2]%pid),"approved"))
    conn.commit()
    print("proposal created")

if __name__=="__main__":
    main()
