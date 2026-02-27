#!/usr/bin/env bash
set -euo pipefail

DB="${DB:-data/openclaw.db}"
SCORE_MIN="${SCORE_MIN:-70}"
CONTACTS_HEURISTIC_FILL="${CONTACTS_HEURISTIC_FILL:-1}"
AUTO_NO_CONTACTS_ZERO="${AUTO_NO_CONTACTS_ZERO:-1}"
NO_MIN_AGE_MIN="${NO_MIN_AGE_MIN:-180}"
NO_REQUIRE_REAL_CONTACTS="${NO_REQUIRE_REAL_CONTACTS:-1}"

scripts/backfill_opportunity_from_items.sh >/dev/null 2>&1 || true

sqlite3 "$DB" -csv "select item_id from opportunity where score_total >= $SCORE_MIN and gate='none';" \
| awk -F, 'NF&&$1!=""{print $1}' \
| while read -r id; do
  scripts/meet_open.sh "$id" >/dev/null 2>&1 || true
done

sqlite3 "$DB" -csv "select item_id from opportunity where gate='meet';" \
| awk -F, 'NF&&$1!=""{print $1}' \
| while read -r id; do
  scripts/jobs_apply_scout_contacts.sh "$id" >/dev/null 2>&1 || true
  if [ "$CONTACTS_HEURISTIC_FILL" = "1" ]; then
    scripts/contacts_backfill_basic.sh "$id" >/dev/null 2>&1 || true
  fi
done

if [ "$AUTO_NO_CONTACTS_ZERO" = "1" ] && [ "$NO_REQUIRE_REAL_CONTACTS" != "1" ]; then
  sqlite3 "$DB" -csv "select o.item_id
  from opportunity o
  join opportunity_meeting m on m.item_id=o.item_id and m.status='new'
  where o.gate='meet'
    and m.created_at <= datetime('now','-'||$NO_MIN_AGE_MIN||' minutes')
    and (select count(*) from contacts c where c.item_url=(select url from items where id=o.item_id) and c.source<>'heuristic')=0;" \
  | awk -F, 'NF&&$1!=""{print $1}' \
  | while read -r id; do
    scripts/meet_close.sh "$id" no "contactsゼロ" >/dev/null 2>&1 || true
  done
fi
