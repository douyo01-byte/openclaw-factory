import os,sqlite3,urllib.request,urllib.parse,json,re,time

DB_PATH=os.environ.get("DB_PATH","data/openclaw.db")
TOKEN=os.environ.get("TELEGRAM_BOT_TOKEN","").strip()
API=f"https://api.telegram.org/bot{TOKEN}/getUpdates"

def conn():
    return sqlite3.connect(DB_PATH,timeout=30)

def extract_pid(text):
    m=re.search(r'#(\d+)',text or "")
    return int(m.group(1)) if m else None

def save_conversation(c,pid,text):
    c.execute("""
    insert into proposal_conversation(proposal_id,role,message,created_at)
    values(?,?,?,datetime('now'))
    """,(pid,"human",text))

def update_state(c,pid):
    row=c.execute("""
    select stage from proposal_state where proposal_id=?
    """,(pid,)).fetchone()
    if row and row[0]=="waiting_answer":
        c.execute("""
        update proposal_state
        set stage='answer_received',updated_at=datetime('now')
        where proposal_id=?
        """,(pid,))

def tick():
    offset=0
    try:
        with urllib.request.urlopen(API,timeout=30) as r:
            data=json.loads(r.read().decode())
    except:
        return
    if not data.get("ok"):
        return
    for u in data.get("result",[]):
        msg=u.get("message",{})
        text=msg.get("text","")
        pid=extract_pid(text)
        if not pid:
            continue
        c=conn()
        save_conversation(c,pid,text)
        update_state(c,pid)
        c.commit()
        c.close()

if __name__=="__main__":
    tick()
