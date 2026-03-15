import sqlite3,os,time

DB=os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db")

def get_recent_success(conn):
    return conn.execute("""
    select p.id,p.title,l.result_score
    from learning_results l
    join dev_proposals p on p.id=l.proposal_id
    where l.result_score>=2
    order by l.created_at desc
    limit 50
    """).fetchall()

def analyze(rows):
    buckets={}
    for r in rows:
        t=r[1].lower()
        if "executor" in t:
            k="executor"
        elif "ai" in t:
            k="ai"
        elif "self" in t:
            k="self_improve"
        else:
            k="other"
        buckets[k]=buckets.get(k,0)+1
    return buckets

def write_bias(conn,buckets):
    for k,v in buckets.items():
        conn.execute("""
        insert or replace into supply_bias(bias_type,bias_key,weight,source_pattern_count,updated_at)
        values('reasoning',?, ?, ?,datetime('now'))
        """,(k,v*10,v))

def main():
    while True:
        try:
            conn=sqlite3.connect(DB,timeout=30)
            rows=get_recent_success(conn)
            b=analyze(rows)
            write_bias(conn,b)
            conn.commit()
            conn.close()
        except:
            pass
        time.sleep(300)

if __name__=="__main__":
    main()
