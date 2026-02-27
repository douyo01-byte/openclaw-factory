import os,sqlite3,re,math,collections

DB=os.environ.get("DB_PATH","data/openclaw.db")

def tok(s):
    s=(s or "").lower()
    s=s.replace("／","/").replace("　"," ")
    out=[]
    out+=re.findall(r"[a-z0-9][a-z0-9_\-]{2,}",s)
    out+=re.findall(r"(?:https?://)?(?:www\.)?([a-z0-9\-]+\.[a-z0-9\.\-]+)",s)
    out+=re.findall(r"[ァ-ヴー]{2,}",s)
    out+=re.findall(r"[一-龥]{2,}",s)
    out+=re.findall(r"[ぁ-ん]{3,}",s)
    out=[x.strip(".") for x in out if x and x not in {"http","https","www"}]
    return out

def main():
    conn=sqlite3.connect(DB)
    conn.execute("create table if not exists decision_patterns(token text primary key, weight real not null, updated_at text default (datetime('now')))")
    rows=conn.execute("""
      select decision, reason from decisions
      order by id desc limit 2000
    """).fetchall()

    pos=collections.Counter()
    neg=collections.Counter()

    for d,r in rows:
        d=(d or "").strip()
        t=tok(r or "")
        if not t:
            continue
        if d in {"採用","approve","APPROVE","go","GO"}:
            pos.update(t)
        if d in {"見送り","reject","REJECT","no","NO"}:
            neg.update(t)

    all_tokens=set(pos.keys())|set(neg.keys())
    scored=[]
    for w in all_tokens:
        p=pos[w]
        n=neg[w]
        s=(math.log(1+p)-math.log(1+n))
        if abs(s) < 0.35:
            continue
        scored.append((w,s))

    scored.sort(key=lambda x: abs(x[1]), reverse=True)
    top=scored[:120]

    conn.execute("delete from decision_patterns")
    conn.executemany("insert into decision_patterns(token,weight,updated_at) values(?,?,datetime('now'))", top)
    conn.commit()
    conn.close()

if __name__=="__main__":
    main()
