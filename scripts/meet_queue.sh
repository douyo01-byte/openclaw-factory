#!/usr/bin/env bash
set -euo pipefail
sqlite3 data/openclaw.db "
select
  o.item_id,
  coalesce(i.title,'') as title,
  replace(replace(replace(coalesce(i.url,''),'https://',''),'http://',''),'www.','') as url,
  coalesce(p.product_name,'') as name,
  coalesce(p.target_price_jpy,0) as price,
  coalesce(p.est_cogs_jpy,0) as cogs,
  coalesce(p.ship_jpy,0) as ship,
  coalesce(p.duty_vat_jpy,0) as duty,
  coalesce(p.platform_fee_pct,0) as fee_pct,
  coalesce(p.ads_cac_jpy,0) as ads,
  coalesce(p.returns_pct,0) as ret_pct,
  coalesce(p.other_jpy,0) as other,
  coalesce(p.est_units_month,0) as units,
  coalesce(p.notes,'') as notes,
  o.updated_at
from opportunity o
left join items i on i.id=o.item_id
left join opportunity_plan p on p.item_id=o.item_id
where o.gate='meet'
order by o.updated_at desc
limit 20;
"
