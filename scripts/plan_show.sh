#!/usr/bin/env bash
set -euo pipefail
id="${1:?item_id}"

python - "$id" <<'PY'
import sqlite3,sys,math
id=int(sys.argv[1])
conn=sqlite3.connect("data/openclaw.db")
conn.row_factory=sqlite3.Row

p=conn.execute("select * from opportunity_plan where item_id=?", (id,)).fetchone()
i=conn.execute("select id,title,url from items where id=?", (id,)).fetchone()

if not i:
  print("no item")
  raise SystemExit(1)
if not p:
  print("no plan")
  raise SystemExit(1)

price=int(p["target_price_jpy"] or 0)
cogs=int(p["est_cogs_jpy"] or 0)
ship=int(p["ship_jpy"] or 0)
duty=int(p["duty_vat_jpy"] or 0)
fee_pct=float(p["platform_fee_pct"] or 0)
ads=int(p["ads_cac_jpy"] or 0)
ret_pct=float(p["returns_pct"] or 0)
other=int(p["other_jpy"] or 0)
units=int(p["est_units_month"] or 0)

fee=math.floor(price*fee_pct/100.0)
ret=math.floor(price*ret_pct/100.0)
gp=price-(cogs+ship+duty+fee+ads+ret+other)
pm=0 if price==0 else round(gp/price*100,1)
month=gp*units

title=(i["title"] or "").replace("\n"," ").strip()[:60]
url=(i["url"] or "").replace("https://","").replace("http://","").replace("www.","")[:90]

print(f'{id} {title}')
print(url)
print(f'price{price} cogs{cogs} ship{ship} duty{duty} fee{fee} ads{ads} ret{ret} other{other}')
print(f'gp{gp} pm{pm}% units{units} profit/mo{month}')
conn.close()
PY
