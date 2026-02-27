#!/usr/bin/env bash
set -euo pipefail

msg="$(python - <<'PY'
import sqlite3,plistlib,pathlib,datetime,urllib.parse,re

plist=pathlib.Path.home()/"Library/LaunchAgents/jp.kuu.openclaw.tg_poll.plist"
env=plistlib.loads(plist.read_bytes()).get("EnvironmentVariables",{})
db=env.get("OCLAW_DB_PATH") or "data/openclaw.db"

conn=sqlite3.connect(db)
conn.row_factory=sqlite3.Row

now=datetime.datetime.now().strftime("%m-%d %H:%M")

new_24h=conn.execute("select count(1) c from items where created_at>=datetime('now','-1 day')").fetchone()["c"]
reviewed_24h=conn.execute("""
select count(1) c from (
  select item_id from decision_events
  where decided_at>=datetime('now','-1 day')
  group by item_id
)
""").fetchone()["c"]

m={"採用":"A","保留":"H","却下":"R","adopt":"A","hold":"H","reject":"R"}
dec_rows=conn.execute("""
select decision, count(1) n
from decision_events
where decided_at>=datetime('now','-1 day')
group by decision
order by n desc
""").fetchall()
dec_summary="".join([f'{m.get(r["decision"],str(r["decision"])[:1])}{r["n"]}' for r in dec_rows if r["decision"]])

contacts_total=conn.execute("select count(1) c from contacts").fetchone()["c"]
contacts_24h=conn.execute("select count(1) c from contacts where first_seen_at>=datetime('now','-1 day')").fetchone()["c"]
outreach_24h=conn.execute("select count(1) c from outreach_log where sent_at>=datetime('now','-1 day')").fetchone()["c"]

top=conn.execute("""
select coalesce(i.title,'') title, i.url url, coalesce(i.source,'') source, coalesce(m.priority,0) pr
from items i
left join item_meta m on m.item_id=i.id
order by pr desc, i.created_at desc
limit 5
""").fetchall()

row=conn.execute("select text from retrospectives order by id desc limit 1").fetchone()
retro=""
if row and row["text"]:
    t=[x.strip() for x in row["text"].splitlines() if x.strip()]
    for s in reversed(t):
        if s.lower().startswith(("window=","latest:","actions:","[reflection_","latest=")):
            continue
        retro=s
        break
retro=retro.strip()
if retro.startswith("Action:"):
    retro=retro.split(":",1)[1].strip()
if retro.startswith("-"):
    retro=retro[1:].strip()

def tg(url):
    h=urllib.parse.urlparse(url).netloc.lower()
    if "github.com" in h: return "gh"
    if "producthunt.com" in h: return "ph"
    if "reddit.com" in h: return "rd"
    return "w"

def ac(url):
    t=tg(url)
    if t=="rd": return "X"
    if t in ("gh","ph"): return "S"
    return "C"

def su(url):
    u=url.strip()
    u=re.sub(r"^https?://","",u)
    u=re.sub(r"^www\.","",u)
    if u.startswith("reddit.com/"):
        m2=re.search(r"(reddit\.com/r/[^/]+/comments/[^/]+)",u)
        if m2: u=m2.group(1)
    return u[:86]

out=[]
out.append(f"{now} G3 N{new_24h} R{reviewed_24h} D{dec_summary} C{contacts_total}+{contacts_24h} O{outreach_24h}")
if retro:
    out.append(f"R {retro[:64]}")
for i,r in enumerate(top,1):
    title=(r["title"] or "").strip().replace("\n"," ")
    url=(r["url"] or "").strip()
    pr=int(r["pr"] or 0)
    t=(title[:44] if title else su(url))
    out.append(f"{i} p{pr}{tg(url)}{ac(url)} {t} {su(url)}")

print("\n".join(out).strip())
conn.close()
PY
)"

printf "%s\n" "$msg"
if [ "${NO_SEND:-0}" != "1" ]; then
  printf "%s\n" "$msg" | scripts/tg_send_text.sh >/dev/null
fi
