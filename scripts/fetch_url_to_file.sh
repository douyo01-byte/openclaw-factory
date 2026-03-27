#!/bin/zsh
set -euo pipefail
url="${1:?url required}"
out="${2:?out required}"
mkdir -p "$(dirname "$out")"
curl -L --fail --silent --show-error \
  -A "Mozilla/5.0" \
  "$url" > "$out"
