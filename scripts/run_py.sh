#!/usr/bin/env bash
set -euo pipefail
exec </dev/null
exec >> "${1:?logfile}" 2>&1
shift
exec python -u "$@"
