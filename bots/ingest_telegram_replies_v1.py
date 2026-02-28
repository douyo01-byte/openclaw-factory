import os,json,datetime,urllib.parse,urllib.request,sqlite3
DB_PATH=os.environ.get("DB_PATH","data/openclaw.db")
TOKEN=os.environ.get("TELEGRAM_BOT_TOKEN","").strip()
API=f"https://api.telegram.org/bot{TOKEN}/getUpdates"
def now(): return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def parse_text(text):
 t=(text or "").strip();u=t.upper()
 if not t:return None
 if u.startswith("OK"):d,rest="adopt",t[2:].strip()
 elif u.startswith("NO") or u.startswith("NG"):d,rest="reject",t[2:].strip()
 elif u.startswith("HOLD"):d,rest="hold",t[4:].strip()
 elif t.startswith("採用"):d,rest="adopt",t[2:].strip()
 elif t.startswith("見送り"):d,rest="reject",t[3:].strip()
 elif t.startswith("保留"):d,rest="hold",t[2:].strip()
 else:return None
 target="";reason=""
 if rest:
  p=rest.split(" ",1);target=p[0].strip();reason=p[1].strip() if len(p)>1 else ""
 return d,target,reason
def kv_get(c,k):
 r=c.execute("SELECT v FROM kv WHERE k=?",(k,)).fetchone()
 return r[0] if r else None
def kv_set(c,k,v):
 c.execute("INSERT INTO kv(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",(k,str(v)))
def ensure(c):
 c.execute("PRAGMA journal_mode=WAL;");c.execute("PRAGMA busy_timeout=5000;")
 c.execute("CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL)")
 c.execute("""CREATE TABLE IF NOT EXISTS inbox_commands(
id INTEGER PRIMARY KEY AUTOINCREMENT,
chat_id TEXT,
message_id INTEGER,
reply_to_message_id INTEGER,
from_username TEXT,
from_name TEXT,
text TEXT NOT NULL,
received_at TEXT NOT NULL DEFAULT (datetime('now')),
applied_at TEXT,
status TEXT DEFAULT 'new',
error TEXT)""")
 c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_inbox_chat_msg ON inbox_commands(chat_id,message_id)")
 dc={r[1] for r in c.execute("PRAGMA table_info(decisions)")}
 if "run_id" not in dc:c.execute("ALTER TABLE decisions ADD COLUMN run_id TEXT")
 if "target" not in dc:c.execute("ALTER TABLE decisions ADD COLUMN target TEXT")
 if "meta_json" not in dc:c.execute("ALTER TABLE decisions ADD COLUMN meta_json TEXT")
def http_get(url,params):
 qs=urllib.parse.urlencode(params,safe='[]",')
 with urllib.request.urlopen(urllib.request.Request(f"{url}?{qs}"),timeout=30) as r:
  return json.loads(r.read().decode())
def main():
 if not TOKEN:raise SystemExit("TELEGRAM_BOT_TOKEN empty")
 c=sqlite3.connect(DB_PATH);ensure(c)
 offset=kv_get(c,"tg_offset");params={"timeout":0,"allowed_updates":'["message"]'}
 if offset is not None:params["offset"]=int(offset)
 data=http_get(API,params);updates=data.get("result") or [];max_uid=None
 for upd in updates:
  uid=upd.get("update_id");msg=upd.get("message") or {}
  if uid is None:continue
  max_uid=uid if max_uid is None else max(max_uid,uid)
  chat=msg.get("chat") or {};frm=msg.get("from") or {};text=msg.get("text") or ""
  chat_id=str(chat.get("id",""));message_id=int(msg.get("message_id") or 0)
  reply_id=int(((msg.get("reply_to_message") or {}).get("message_id")) or 0)
  from_username=str(frm.get("username") or "");from_name=str(frm.get("first_name") or "")
  c.execute("INSERT OR IGNORE INTO inbox_commands(chat_id,message_id,reply_to_message_id,from_username,from_name,text,received_at) VALUES(?,?,?,?,?,?,?)",(chat_id,message_id,reply_id,from_username,from_name,text,now()))
  p=parse_text(text)
  if p:
   decision,target,reason=p
   meta={"chat_id":chat.get("id"),"message_id":message_id,"update_id":uid,"raw":text}
   c.execute("INSERT INTO decisions(run_id,target,decision,reason,meta_json,created_at) VALUES(?,?,?,?,?,?)",(os.environ.get("RUN_ID"),target,decision,reason,json.dumps(meta,ensure_ascii=False),now()))
 if max_uid is not None:kv_set(c,"tg_offset",int(max_uid)+1)
 c.commit();c.close()
if __name__=="__main__":main()
