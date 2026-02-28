#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
test -f ./.env.openclaw && set -a && . ./.env.openclaw && set +a
exec "$@"
