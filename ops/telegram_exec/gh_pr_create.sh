#!/bin/bash
set -euo pipefail
title="${1:-}"
body="${2:-}"
base="${3:-main}"
[ -n "$title" ] || { echo "missing title"; exit 1; }
tmp=$(mktemp)
printf '%s\n' "$body" > "$tmp"
gh pr create --base "$base" --title "$title" --body-file "$tmp"
rm -f "$tmp"
