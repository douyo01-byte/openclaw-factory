#!/bin/bash
DB_PATH="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"

sqlite3 "$DB_PATH" "
select title, status, score
from adoption_candidates
order by id desc
limit 10;
"
