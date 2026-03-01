#!/usr/bin/env bash
set -euo pipefail
log="${1:?logfile}"
shift
exec 0</dev/null
exec 1>>"$log"
exec 2>&1
exec python -u "$@"
