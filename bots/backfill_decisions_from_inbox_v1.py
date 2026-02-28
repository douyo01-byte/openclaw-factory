import os, json, sqlite3, datetime
DB_PATH=os.environ.get("DB_PATH","data/openclaw.db")

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def cols(con, t):
    return [r[1] for r in con.execute(f"pragma table_info({t})")]

def parse_text(text):
    t=(text or "").strip()
    if not t: return None
    u=t.upper()
    if u.startswith("OK"):
        d="adopt"; rest=t[2:].strip()
    elif u.startswith("NO") or u.startswith("NG"):
        d="reject"; rest=t[2:].strip()
    elif u.startswith("HOLD"):
        d="hold"; rest=t[4:].strip()
    elif t.startswith("採用"):
        d="adopt"; rest=t[len("採用"):].strip()
    elif t.startswith("見送り"):
        d="reject"; rest=t[len("見送り"):].strip()
    elif t.startswith("保留"):
        d="hold"; rest=t[len("保留"):].strip()
    elif t.startswith("A"):
        d="adopt"; rest=t[1:].strip()
    else:
        return None
    target=""; reason=""
    if rest:
        parts=rest.split(" ",1)
        target=parts[0].strip()
        reason=(parts[1].strip() if len(parts)>1 else "")
    return d,target,reason

con=sqlite3.connect(DB_PATH)
con.execute("PRAGMA journal_mode=WAL;")
con.execute("PRAGMA busy_timeout=5000;")

c=set(cols(con,"inbox_commands"))
sel=[]
if "update_id" in c: sel.append("update_id")
if "chat_id" in c: sel.append("chat_id")
if "user_id" in c: sel.append("user_id")
if "text" in c: sel.append("text")
if "received_at" in c: sel.append("received_at")
q="SELECT " + ",".join(sel) + " FROM inbox_commands ORDER BY id ASC"
rows=con.execute(q).fetchall()

ins=0
for row in rows:
    m=dict(zip(sel,row))
    text=m.get("text","")
    p=parse_text(text)
    if not p:
        continue
    d,target,reason=p
    upd=m.get("update_id","")
    key=f'"update_id": {int(upd)}' if str(upd).isdigit() else f'"update_id": "{upd}"'
    exists=con.execute("SELECT 1 FROM decisions WHERE meta_json LIKE ? LIMIT 1", (f"%{key}%",)).fetchone()
    if exists:
        continue
    meta={"chat_id":m.get("chat_id"),"user_id":m.get("user_id"),"raw":text,"update_id":int(upd) if str(upd).isdigit() else upd}
    con.execute(
        "INSERT INTO decisions(run_id,target,decision,reason,meta_json,created_at) VALUES(?,?,?,?,?,?)",
        (os.environ.get("RUN_ID"), target, d, reason, json.dumps(meta,ensure_ascii=False), m.get("received_at") or now())
    )
    ins+=1
con.commit()
print(ins)
