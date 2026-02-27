import sqlite3, os

def _db():
    return sqlite3.connect(os.environ.get("DB_PATH","data/openclaw.db"))

def learn(topic, content, source, confidence=0.7):
    conn=_db()
    conn.execute("insert into learnings(topic,content,source,confidence) values(?,?,?,?)",(topic,content,source,confidence))
    conn.commit()
    conn.close()

def get_learnings(topic,limit=20):
    conn=_db()
    rows=conn.execute("select content from learnings where topic=? order by id desc limit ?",(topic,limit)).fetchall()
    conn.close()
    return "\n".join([r[0] for r in rows])

def save_decision(product_id, decision, reason):
    conn=_db()
    conn.execute("insert into decisions(product_id,decision,reason) values(?,?,?)",(product_id,decision,reason))
    conn.commit()
    conn.close()

def recall(topic,limit=20):
    conn=_db()
    rows=conn.execute("select content from learnings where topic like ? order by id desc limit ?",(f"%{topic}%",limit)).fetchall()
    conn.close()
    return "\n".join([r[0] for r in rows])

def recall_decisions(limit=30):
    conn=_db()
    rows=conn.execute("select decision||':'||reason from decisions order by id desc limit ?",(limit,)).fetchall()
    conn.close()
    return "\n".join([r[0] for r in rows])

def recall_success_patterns(limit=50):
    conn=_db()
    rows=conn.execute("""
        select reason from decisions
        where decision like '%APPROVE%' or decision like '%GO%'
        order by id desc limit ?
    """,(limit,)).fetchall()
    conn.close()
    return "\n".join([r[0] for r in rows])

def recall_decision_patterns(limit=60):
    conn=_db()
    rows=conn.execute("select token,weight from decision_patterns order by abs(weight) desc limit ?",(limit,)).fetchall()
    conn.close()
    return "\n".join([f"{t}:{w:.2f}" for t,w in rows])
