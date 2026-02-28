#!/usr/bin/env bash
set -euo pipefail
id="${1:?item_id}"
name="${2:-}"
price="${3:-0}"
cogs="${4:-0}"
ship="${5:-0}"
duty="${6:-0}"
fee_pct="${7:-0}"
ads="${8:-0}"
ret_pct="${9:-0}"
other="${10:-0}"
units="${11:-0}"

sqlite3 data/openclaw.db <<SQL
INSERT INTO opportunity_plan(
  item_id,product_name,target_price_jpy,est_cogs_jpy,ship_jpy,duty_vat_jpy,platform_fee_pct,ads_cac_jpy,returns_pct,other_jpy,est_units_month,updated_at
) VALUES(
  $id,'$name',$price,$cogs,$ship,$duty,$fee_pct,$ads,$ret_pct,$other,$units,datetime('now')
)
ON CONFLICT(item_id) DO UPDATE SET
  product_name=excluded.product_name,
  target_price_jpy=excluded.target_price_jpy,
  est_cogs_jpy=excluded.est_cogs_jpy,
  ship_jpy=excluded.ship_jpy,
  duty_vat_jpy=excluded.duty_vat_jpy,
  platform_fee_pct=excluded.platform_fee_pct,
  ads_cac_jpy=excluded.ads_cac_jpy,
  returns_pct=excluded.returns_pct,
  other_jpy=excluded.other_jpy,
  est_units_month=excluded.est_units_month,
  updated_at=datetime('now');
SQL
