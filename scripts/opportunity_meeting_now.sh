#!/usr/bin/env bash
set -euo pipefail

msg="$(python - <<'PY'
import sqlite3,datetime
conn=sqlite3.connect("data/openclaw.db")
conn.row_factory=sqlite3.Row

now=datetime.datetime.now().strftime("%m-%d %H:%M")
meeting_key=datetime.datetime.now().strftime("%Y-%m-%d")

rows=conn.execute("""
select
  i.id item_id,
  coalesce(m.priority,0) pr,
  i.title,
  i.url,
  (select count(1) from contacts c where c.item_url=i.url) contacts_n
from opportunity o
join items i on i.id=o.item_id
left join item_meta m on m.item_id=i.id
where o.gate='meet'
order by pr desc, i.created_at desc
limit 8
""").fetchall()

out=[f"{now} MEET"]
if not rows:
  out.append("0")
  print("\n".join(out).strip())
  conn.close()
  raise SystemExit(0)

for r in rows:
  title=(r["title"] or "").replace("\n"," ").strip()[:52]
  url=(r["url"] or "").replace("https://","").replace("http://","").replace("www.","").strip()[:90]
  out.append(f'{r["item_id"]} p{r["pr"]} c{r["contacts_n"]} {title} {url}')

out.append("DECIDE: jp_channel price cogs ship fee ads unit/mo go/no-go owner")
msg="\n".join(out).strip()

for r in rows:
  conn.execute("""
    insert or ignore into opportunity_meeting(item_id,meeting_key,agenda,status,created_at)
    values(?,?,?,?,datetime('now'))
  """,(r["item_id"],meeting_key,msg,"new"))

conn.commit()
conn.close()
print(msg)
PY
)"

printf "%s\n" "$msg"
if [ "${NO_SEND:-0}" != "1" ]; then
  printf "%s\n" "$msg" | scripts/tg_send_text.sh >/dev/null
fi
